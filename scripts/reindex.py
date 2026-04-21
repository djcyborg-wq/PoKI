import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.vector_store import get_vector_store
from backend.metadata_db import get_metadata_db
from scripts.init_index import main as init_main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("RKI Document Re-Index")
    logger.info("=" * 50)
    
    logger.info("Loesche bestehenden Index...")
    
    try:
        store = get_vector_store()
        store.initialize()
        store.clear_all()
        logger.info("Vector Store geleert")
    except Exception as e:
        logger.error(f"Fehler beim Leeren des Vector Store: {e}")
    
    try:
        db = get_metadata_db()
        db.clear_all()
        logger.info("Metadaten-Datenbank geleert")
    except Exception as e:
        logger.error(f"Fehler beim Leeren der Datenbank: {e}")
    
    logger.info("Starte Neuindizierung...")
    init_main()
    
    logger.info("Re-Index abgeschlossen")


if __name__ == "__main__":
    main()