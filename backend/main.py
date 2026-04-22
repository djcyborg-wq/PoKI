import logging
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings, FolderConfig
from backend.vector_store import get_vector_store
from backend.llm_engine import get_llm_engine
from backend.metadata_db import get_metadata_db
from backend.document_loader import get_loader, get_all_files
from backend.text_processor import get_text_processor
from backend.file_watcher import start_file_watcher, stop_file_watcher


logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str
    history: Optional[List[Dict[str, str]]] = None
    top_k: int = Field(default=10, ge=1, le=20)
    folders: Optional[List[str]] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    query_time_ms: int


class FolderRequest(BaseModel):
    path: str
    enabled: bool = True


class FolderUpdateRequest(BaseModel):
    enabled: Optional[bool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PoKI API...")
    
    errors = settings.validate_folders()
    if errors:
        for error in errors:
            logger.warning(f"Folder validation: {error}")
    
    try:
        folders = [{'path': f.path, 'id': f.id, 'enabled': f.enabled} 
                  for f in settings.get_active_folders()]
        start_file_watcher(folders)
    except Exception as e:
        logger.error(f"Failed to start file watcher: {e}")
    
    yield
    
    logger.info("Shutting down...")
    stop_file_watcher()


app = FastAPI(
    title="PoKI - Private KI Dokumentassistent",
    description="Lokale KI-gestützte Dokumentensuche mit Ollama und RAG",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/", response_class=FileResponse)
async def root():
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/api/health")
async def health_check():
    llm = get_llm_engine()
    ollama_ok = llm.is_available()
    
    try:
        store = get_vector_store()
        store.initialize()
        store_ok = True
    except Exception:
        store_ok = False
    
    return {
        "status": "ok" if (ollama_ok and store_ok) else "degraded",
        "ollama": "connected" if ollama_ok else "unavailable",
        "model": llm.model,
        "vector_store": "ready" if store_ok else "error"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start_time = time.time()
    
    try:
        llm = get_llm_engine()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {str(e)}")
    
    if not llm.is_available():
        raise HTTPException(status_code=503, detail="Ollama service not available")
    
    try:
        store = get_vector_store()
        store.initialize()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Vector store error: {str(e)}")
    
    results = store.search(
        query=request.question,
        top_k=request.top_k,
        folder_filter=request.folders
    )
    
    if not results:
        return ChatResponse(
            answer="Ich finde keine Informationen dazu in den Dokumenten.",
            sources=[],
            query_time_ms=int((time.time() - start_time) * 1000)
        )
    
    context_parts = []
    sources = []
    
    for i, result in enumerate(results):
        context_parts.append(f"[{i+1}] {result['content']}")
        
        meta = result.get('metadata', {})
        sources.append({
            "file": meta.get('filename', 'Unknown'),
            "folder": meta.get('folder_source', 'Unknown'),
            "snippet": result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
        })
    
    context = "\n\n---\n\n".join(context_parts)
    
    logger.info(f"Chat request - model: {llm.model}, context length: {len(context)}")
    
    try:
        answer = llm.chat(
            question=request.question,
            context=context,
            history=request.history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    
    return ChatResponse(
        answer=answer,
        sources=sources,
        query_time_ms=int((time.time() - start_time) * 1000)
    )


@app.get("/api/documents")
async def get_documents(folders: Optional[str] = None):
    folder_list = folders.split(",") if folders else None
    
    db = get_metadata_db()
    files = db.get_all_files(folder_filter=folder_list)
    
    return {"documents": files, "count": len(files)}


@app.get("/api/stats")
async def get_stats():
    try:
        store = get_vector_store()
        store.initialize()
        store_stats = store.get_stats()
    except Exception:
        store_stats = {"total_chunks": 0, "folder_counts": {}}
    
    try:
        db = get_metadata_db()
        folder_stats = db.get_folder_stats()
    except Exception:
        folder_stats = {}
    
    active_folders = settings.get_active_folders()
    
    return {
        "total_chunks": store_stats.get("total_chunks", 0),
        "folder_counts": store_stats.get("folder_counts", {}),
        "document_stats": folder_stats,
        "configured_folders": len(active_folders)
    }


@app.get("/api/folders")
async def get_folders():
    folders = settings.get_active_folders()
    
    db = get_metadata_db()
    folder_stats = db.get_folder_stats()
    
    result = []
    for folder in folders:
        stats = folder_stats.get(folder.path, {})
        result.append({
            "id": folder.id,
            "path": folder.path,
            "enabled": folder.enabled,
            "document_count": stats.get("document_count", 0),
            "total_chunks": stats.get("total_chunks", 0)
        })
    
    return {"folders": result}


@app.post("/api/folders", status_code=201)
async def add_folder(request: FolderRequest, background_tasks: BackgroundTasks):
    path = request.path.strip()
    
    if not Path(path).exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
    
    current_folders = settings.get_folders_list()
    
    for f in current_folders:
        if f.path.lower() == path.lower():
            raise HTTPException(status_code=400, detail="Folder already configured")
    
    new_folder = FolderConfig(
        path=path,
        enabled=request.enabled,
        id=f"folder_{len(current_folders)}"
    )
    
    current_folders.append(new_folder)
    settings.save_folders(current_folders)
    
    background_tasks.add_task(index_folder, path)
    
    return {"id": new_folder.id, "path": path, "message": "Folder added, indexing started"}


@app.put("/api/folders/{folder_id}")
async def update_folder(folder_id: str, request: FolderUpdateRequest):
    folders = settings.get_folders_list()
    
    for i, f in enumerate(folders):
        if f.id == folder_id:
            if request.enabled is not None:
                folders[i].enabled = request.enabled
                settings.save_folders(folders)
            return {"message": "Folder updated"}
    
    raise HTTPException(status_code=404, detail="Folder not found")


@app.delete("/api/folders/{folder_id}")
async def delete_folder(folder_id: str, delete_index: bool = True):
    folders = settings.get_folders_list()
    
    folder_to_delete = None
    for i, f in enumerate(folders):
        if f.id == folder_id:
            folder_to_delete = f
            del folders[i]
            break
    
    if folder_to_delete is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    settings.save_folders(folders)
    
    if delete_index:
        try:
            store = get_vector_store()
            store.initialize()
            db = get_metadata_db()
            
            files = db.get_all_files(folder_filter=[folder_to_delete.path])
            for file in files:
                store.delete_by_source(file['path'])
                db.delete_file(file['path'])
        except Exception as e:
            logger.error(f"Error deleting index: {e}")
    
    return {"message": "Folder deleted"}


@app.post("/api/reindex")
async def reindex_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_do_reindex)
    return {"message": "Reindex started"}


def _do_reindex():
    logger.info("Starting full reindex...")
    
    try:
        store = get_vector_store()
        store.initialize()
        store.clear_all()
        
        # Wichtig: Nach clear_all() neu initialisieren
        store.initialize()
        
        db = get_metadata_db()
        db.clear_all()
        
        folders = settings.get_active_folders()
        for folder in folders:
            index_folder(folder.path)
        
        logger.info("Reindex completed")
    except Exception as e:
        logger.error(f"Reindex error: {e}")


def index_folder(folder_path: str):
    logger.info(f"Indexing folder: {folder_path}")
    
    try:
        files = get_all_files(folder_path, recursive=True)
        logger.info(f"Found {len(files)} files in {folder_path}")
        
        loader = get_loader()
        processor = get_text_processor()
        store = get_vector_store()
        store.initialize()
        db = get_metadata_db()
        
        for file_path in files:
            if not loader.is_supported(file_path):
                continue
            
            try:
                doc = loader.load(file_path, folder_path)
                chunks = processor.process_document(doc['content'], doc['metadata'])
                
                if chunks:
                    store.add_documents(chunks)
                    
                    db.add_file(
                        path=file_path,
                        filename=Path(file_path).name,
                        file_type=Path(file_path).suffix,
                        size=doc['metadata'].get('size', 0),
                        folder_source=folder_path,
                        status='indexed'
                    )
                    db.update_file_status(file_path, 'indexed', len(chunks))
                    
                    logger.info(f"Indexed: {file_path}")
            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")
                db.add_file(
                    path=file_path,
                    filename=Path(file_path).name,
                    file_type=Path(file_path).suffix,
                    size=0,
                    folder_source=folder_path,
                    status='error'
                )
                db.update_file_status(file_path, 'error', error_message=str(e))
        
        logger.info(f"Finished indexing {folder_path}")
    except Exception as e:
        logger.error(f"Error indexing folder {folder_path}: {e}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False
    )