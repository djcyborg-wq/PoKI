import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.document_loader import get_loader, get_all_files
from backend.text_processor import get_text_processor
from backend.vector_store import get_vector_store
from backend.metadata_db import get_metadata_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("RKI Document Index Initialisierung")
    logger.info("=" * 50)
    
    folders = settings.get_active_folders()
    
    if not folders:
        logger.error("Keine Dokumenten-Ordner konfiguriert!")
        logger.info("Bitte DOCUMENT_FOLDERS in .env setzen")
        return
    
    logger.info(f"Gefundene Ordner: {len(folders)}")
    
    loader = get_loader()
    processor = get_text_processor()
    store = get_vector_store()
    db = get_metadata_db()
    
    logger.info("Initialisiere Vector Store...")
    store.initialize()
    
    total_files = 0
    total_chunks = 0
    errors = 0
    
    for folder in folders:
        logger.info("-" * 40)
        logger.info(f"Indiziere Ordner: {folder.path}")
        
        if not Path(folder.path).exists():
            logger.error(f"Ordner existiert nicht: {folder.path}")
            continue
        
        try:
            files = get_all_files(folder.path, recursive=True)
            logger.info(f"Gefundene Dateien: {len(files)}")
            
            folder_errors = 0
            folder_chunks = 0
            
            for i, file_path in enumerate(files):
                if not loader.is_supported(file_path):
                    continue
                
                if (i + 1) % 10 == 0:
                    logger.info(f"  Fortschritt: {i + 1}/{len(files)}")
                
                try:
                    doc = loader.load(file_path, folder.path)
                    chunks = processor.process_document(doc['content'], doc['metadata'])
                    
                    if chunks:
                        store.add_documents(chunks)
                        folder_chunks += len(chunks)
                        
                        db.add_file(
                            path=file_path,
                            filename=Path(file_path).name,
                            file_type=Path(file_path).suffix,
                            size=doc['metadata'].get('size', 0),
                            folder_source=folder.path,
                            status='indexed'
                        )
                        db.update_file_status(
                            file_path, 'indexed', len(chunks)
                        )
                    else:
                        logger.warning(f"  Keine Chunks extrahiert: {file_path}")
                        
                except Exception as e:
                    folder_errors += 1
                    logger.error(f"  Fehler bei {file_path}: {e}")
                    
                    db.add_file(
                        path=file_path,
                        filename=Path(file_path).name,
                        file_type=Path(file_path).suffix,
                        size=0,
                        folder_source=folder.path,
                        status='error'
                    )
                    db.update_file_status(
                        file_path, 'error', error_message=str(e)
                    )
            
            logger.info(f"  Ergebnis: {len(files)} Dateien, {folder_chunks} Chunks, {folder_errors} Fehler")
            
            total_files += len(files)
            total_chunks += folder_chunks
            errors += folder_errors
            
        except Exception as e:
            logger.error(f"Fehler beim Indizieren von {folder.path}: {e}")
    
    logger.info("=" * 50)
    logger.info("ZUSAMMENFASSUNG")
    logger.info("=" * 50)
    logger.info(f"Gesamt Dateien: {total_files}")
    logger.info(f"Gesamt Chunks: {total_chunks}")
    logger.info(f"Fehler: {errors}")
    logger.info("=" * 50)
    
    stats = store.get_stats()
    logger.info(f"Vector Store Stats: {stats}")


if __name__ == "__main__":
    main()