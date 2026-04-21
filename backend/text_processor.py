import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TextProcessor:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        text = re.sub(r'[^\x20-\x7E\xA0-\xFF\u00C0-\u024FäöüÄÖÜß]', '', text)
        
        return text
    
    def split_into_chunks(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        cleaned_content = self.clean_text(content)
        
        if not cleaned_content:
            return []
        
        chunks = []
        
        paragraphs = cleaned_content.split('\n\n')
        
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunk_id = len(chunks)
                    chunks.append({
                        'content': current_chunk,
                        'metadata': {
                            **metadata,
                            'chunk_id': chunk_id,
                            'chunk_count': 0
                        }
                    })
                
                while len(para) > self.chunk_size:
                    sub_chunk = para[:self.chunk_size]
                    chunk_id = len(chunks)
                    chunks.append({
                        'content': sub_chunk,
                        'metadata': {
                            **metadata,
                            'chunk_id': chunk_id,
                            'chunk_count': 0
                        }
                    })
                    para = para[self.chunk_size - self.chunk_overlap:]
                
                current_chunk = para
        
        if current_chunk:
            chunk_id = len(chunks)
            chunks.append({
                'content': current_chunk,
                'metadata': {
                    **metadata,
                    'chunk_id': chunk_id,
                    'chunk_count': 0
                }
            })
        
        for chunk in chunks:
            chunk['metadata']['chunk_count'] = len(chunks)
        
        return chunks
    
    def process_document(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        cleaned_content = self.clean_text(content)
        
        if not cleaned_content:
            logger.warning(f"No content after cleaning for {metadata.get('source_path', 'unknown')}")
            return []
        
        return self.split_into_chunks(cleaned_content, metadata)


class EmbeddingProcessor:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._embedding_dim = None
    
    @property
    def embedding_dim(self) -> int:
        if self._embedding_dim is None:
            self._embedding_dim = 384
        return self._embedding_dim
    
    def load_model(self):
        if self.model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self._embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def create_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        if self.model is None:
            self.load_model()
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 10
        )
        
        return [emb.tolist() for emb in embeddings]
    
    def create_embedding(self, text: str) -> List[float]:
        if self.model is None:
            self.load_model()
        
        embedding = self.model.encode([text])
        return embedding[0].tolist()


_processor = None
_embedding_processor = None


def get_text_processor() -> TextProcessor:
    global _processor
    if _processor is None:
        from backend.config import settings
        _processor = TextProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
    return _processor


def get_embedding_processor() -> EmbeddingProcessor:
    global _embedding_processor
    if _embedding_processor is None:
        from backend.config import settings
        _embedding_processor = EmbeddingProcessor(
            model_name=settings.ollama_embedding_model
        )
    return _embedding_processor