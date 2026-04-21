import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from backend.config import settings
from backend.text_processor import get_embedding_processor

logger = logging.getLogger(__name__)

_import_error = None
try:
    import chromadb
except Exception as e:
    chromadb = None
    _import_error = str(e)


class VectorStore:
    def __init__(self, store_type: str = "chroma"):
        self.store_type = store_type
        self.client = None
        self.collection = None
        self._embedding_processor = None
    
    def initialize(self):
        if self.client is not None:
            return
        
        if self.store_type == "chroma":
            self._init_chroma()
        elif self.store_type == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"Unknown store type: {self.store_type}")
    
    def _init_chroma(self):
        if chromadb is None:
            raise ImportError(f"chromadb is not installed: {_import_error}")
        
        persist_dir = settings.get_vector_store_dir()
        
        self.client = chromadb.PersistentClient(
            path=str(persist_dir)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"description": "RKI Document chunks"}
        )
        
        logger.info(f"Initialized ChromaDB at {persist_dir}")
    
    def _init_faiss(self):
        logger.warning("FAISS store type not fully implemented, falling back to ChromaDB")
        self._init_chroma()
    
    @property
    def embedding_processor(self):
        if self._embedding_processor is None:
            self._embedding_processor = get_embedding_processor()
        return self._embedding_processor
    
    def add_documents(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        if self.collection is None:
            self.initialize()
        
        if not chunks:
            return []
        
        texts = [chunk['content'] for chunk in chunks]
        
        if embeddings is None:
            embeddings = self.embedding_processor.create_embeddings(
                texts,
                batch_size=settings.embedding_batch_size
            )
        
        ids = []
        metadatas = []
        documents = []
        
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            metadatas.append(chunk['metadata'])
            documents.append(chunk['content'])
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        logger.info(f"Added {len(chunks)} chunks to vector store")
        
        return ids
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        folder_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        if self.collection is None:
            self.initialize()
        
        query_embedding = self.embedding_processor.create_embedding(query)
        
        where_clause = None
        if folder_filter:
            where_clause = {
                "$or": [
                    {"folder_source": {"$eq": folder}}
                    for folder in folder_filter
                ]
            }
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        output = []
        
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                output.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else 0.0
                })
        
        return output
    
    def delete_by_source(self, source_path: str) -> bool:
        if self.collection is None:
            self.initialize()
        
        try:
            results = self.collection.get(where={"source_path": {"$eq": source_path}})
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for {source_path}")
                return True
        except Exception as e:
            logger.error(f"Error deleting {source_path}: {e}")
        
        return False
    
    def clear_all(self) -> None:
        if self.client is not None:
            self.client.reset()
            logger.info("Cleared all documents from vector store")
    
    def get_stats(self) -> Dict[str, Any]:
        if self.collection is None:
            self.initialize()
        
        try:
            total = self.collection.count()
            
            all_items = self.collection.get()
            
            folder_counts = {}
            
            if all_items['metadatas']:
                for meta in all_items['metadatas']:
                    folder = meta.get('folder_source', 'unknown')
                    folder_counts[folder] = folder_counts.get(folder, 0) + 1
            
            return {
                'total_chunks': total,
                'folder_counts': folder_counts
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_chunks': 0,
                'folder_counts': {}
            }
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        if self.collection is None:
            self.initialize()
        
        try:
            results = self.collection.get()
            
            documents = []
            
            if results['documents']:
                for i, doc in enumerate(results['documents']):
                    documents.append({
                        'content': doc,
                        'metadata': results['metadatas'][i],
                        'id': results['ids'][i]
                    })
            
            return documents
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            return []


_store = None


def get_vector_store(store_type: Optional[str] = None) -> VectorStore:
    global _store
    if _store is None:
        st = store_type or settings.vector_store_type
        _store = VectorStore(store_type=st)
    return _store