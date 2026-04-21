import logging
from typing import Dict, Any, Optional, List, AsyncIterator
import requests
import json

from backend.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent, der Fragen basierend auf den bereitgestellten Dokumenten beantwortet.

Regeln:
- Antworte nur mit Informationen aus dem bereitgestellten Kontext
- Wenn die Information nicht im Kontext enthalten ist, sage "Ich finde keine Information dazu in den Dokumenten."
- Verwende deutsche Sprache für die Antwort
- Strukturiere die Antwort klar und präzise
- Nenne die Quelle(n) wenn möglich"""


class LLMEngine:
    def __init__(
        self,
        base_url: str = None,
        model: str = None
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self._chat_url = f"{self.base_url}/api/chat"
        self._embed_url = f"{self.base_url}/api/embeddings"
        self._tags_url = f"{self.base_url}/api/tags"
        logger.info(f"LLMEngine initialized with model: {self.model}, url: {self.base_url}")
    
    def is_available(self) -> bool:
        try:
            response = requests.get(self._tags_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def chat(
        self,
        question: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        prompt = self._build_prompt(question, context, history)
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        try:
            response = requests.post(
                self._chat_url,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('message', {}).get('content', '')
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise
    
    def chat_stream(
        self,
        question: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        prompt = self._build_prompt(question, context, history)
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": True
        }
        
        try:
            response = requests.post(
                self._chat_url,
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get('message', {}).get('content', '')
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            raise
    
    def _build_prompt(
        self,
        question: str,
        context: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        history_text = ""
        if history:
            for msg in history[-5:]:
                role = "Benutzer" if msg.get('role') == 'user' else "Assistent"
                history_text += f"\n{role}: {msg.get('content', '')}"
        
        prompt = f"""Kontext aus den Dokumenten:
---
{context}
---

{history_text}

Frage: {question}

Antworte auf die Frage basierend auf dem Kontext."""
        
        return prompt
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        embeddings = []
        
        for text in texts:
            try:
                response = requests.post(
                    self._embed_url,
                    json={
                        "model": settings.ollama_embedding_model,
                        "prompt": text
                    },
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                embeddings.append(result.get('embedding', []))
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                embeddings.append([0.0] * 768)
        
        return embeddings


_llm_engine = None


def get_llm_engine() -> LLMEngine:
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine