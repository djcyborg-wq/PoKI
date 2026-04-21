import logging
import time
import threading
from typing import List, Callable, Dict, Any, Optional
from pathlib import Path
from queue import Queue, Empty
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from backend.config import settings

logger = logging.getLogger(__name__)


class DocumentEventHandler(FileSystemEventHandler):
    IGNORED_PATTERNS = {'.tmp', '.temp', '~$', '.swp', '.bak', '.crdownload'}
    IGNORED_EXTENSIONS = {'.tmp', '.temp'}
    
    def __init__(
        self,
        folder_path: str,
        callback: Callable[[str, str], None],
        debounce_seconds: int = 3
    ):
        self.folder_path = folder_path
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._event_queue: Queue = Queue()
        self._pending_events: Dict[str, Dict[str, Any]] = {}
        self._debounce_thread: Optional[threading.Thread] = None
        self._running = False
    
    def should_process(self, path: str) -> bool:
        p = Path(path)
        
        if p.name.startswith('~$'):
            return False
        
        ext = p.suffix.lower()
        if ext in self.IGNORED_EXTENSIONS:
            return False
        
        if any(part.startswith('.') for part in p.parts):
            return False
        
        return True
    
    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        if self.should_process(event.src_path):
            self._queue_event(event.src_path, 'created')
    
    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        if self.should_process(event.src_path):
            self._queue_event(event.src_path, 'modified')
    
    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        logger.info(f"File deleted: {event.src_path}")
    
    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
    
    def _queue_event(self, path: str, event_type: str):
        self._pending_events[path] = {
            'type': event_type,
            'time': time.time(),
            'count': self._pending_events.get(path, {}).get('count', 0) + 1
        }
        
        self._event_queue.put(path)
        
        self._start_debounce_thread()
    
    def _start_debounce_thread(self):
        if self._debounce_thread and self._debounce_thread.is_alive():
            return
        
        self._running = True
        self._debounce_thread = threading.Thread(target=self._process_events, daemon=True)
        self._debounce_thread.start()
    
    def _process_events(self):
        while self._running:
            try:
                path = self._event_queue.get(timeout=0.5)
                
                if path not in self._pending_events:
                    continue
                
                event_info = self._pending_events[path]
                elapsed = time.time() - event_info['time']
                
                if elapsed < self.debounce_seconds:
                    time.sleep(self.debounce_seconds - elapsed)
                
                if path in self._pending_events:
                    event_type = self._pending_events[path]['type']
                    del self._pending_events[path]
                    
                    try:
                        self.callback(path, event_type)
                    except Exception as e:
                        logger.error(f"Error processing event for {path}: {e}")
            
            except Empty:
                if not self._pending_events:
                    self._running = False
                    break
    
    def stop(self):
        self._running = False


class FileWatcher:
    def __init__(self):
        self._observers: List[Observer] = []
        self._handlers: List[DocumentEventHandler] = []
        self._running = False
    
    def start(self, folders: List[Dict[str, str]]):
        if self._running:
            logger.warning("FileWatcher already running")
            return
        
        self._running = True
        
        for folder in folders:
            folder_path = folder.get('path')
            if not folder_path:
                continue
            
            if not Path(folder_path).exists():
                logger.warning(f"Folder does not exist: {folder_path}")
                continue
            
            handler = DocumentEventHandler(
                folder_path=folder_path,
                callback=self._handle_file_event,
                debounce_seconds=settings.debounce_seconds
            )
            
            observer = Observer()
            observer.schedule(handler, folder_path, recursive=True)
            observer.start()
            
            self._observers.append(observer)
            self._handlers.append(handler)
            
            logger.info(f"Started watching folder: {folder_path}")
        
        logger.info(f"FileWatcher started with {len(self._observers)} observers")
    
    def _handle_file_event(self, file_path: str, event_type: str):
        from backend.document_loader import get_loader
        
        loader = get_loader()
        
        if not loader.is_supported(file_path):
            return
        
        if event_type == 'deleted':
            pass
        else:
            try:
                folder_source = self._get_folder_source(file_path)
                
                doc = loader.load(file_path, folder_source)
                
                from backend.text_processor import get_text_processor
                from backend.vector_store import get_vector_store
                from backend.metadata_db import get_metadata_db
                
                processor = get_text_processor()
                chunks = processor.process_document(doc['content'], doc['metadata'])
                
                if chunks:
                    store = get_vector_store()
                    store.add_documents(chunks)
                    
                    db = get_metadata_db()
                    db.add_file(
                        path=file_path,
                        filename=Path(file_path).name,
                        file_type=Path(file_path).suffix,
                        size=doc['metadata'].get('size', 0),
                        folder_source=folder_source,
                        status='indexed'
                    )
                    db.update_file_status(
                        path=file_path,
                        status='indexed',
                        chunk_count=len(chunks)
                    )
                    
                    logger.info(f"Indexed: {file_path} ({len(chunks)} chunks)")
            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")
    
    def _get_folder_source(self, file_path: str) -> str:
        path = Path(file_path)
        for obs in self._handlers:
            try:
                rel_path = path.relative_to(Path(obs.folder_path))
                return obs.folder_path
            except ValueError:
                continue
        return str(path.parent)
    
    def stop(self):
        self._running = False
        
        for handler in self._handlers:
            handler.stop()
        
        for observer in self._observers:
            observer.stop()
        
        for observer in self._observers:
            observer.join(timeout=5)
        
        self._observers.clear()
        self._handlers.clear()
        
        logger.info("FileWatcher stopped")


_watcher: Optional[FileWatcher] = None


def get_file_watcher() -> FileWatcher:
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher()
    return _watcher


def start_file_watcher(folders: List[Dict[str, str]]):
    if not settings.enable_file_watcher:
        logger.info("File watcher disabled in config")
        return
    
    watcher = get_file_watcher()
    watcher.start(folders)


def stop_file_watcher():
    watcher = get_file_watcher()
    watcher.stop()