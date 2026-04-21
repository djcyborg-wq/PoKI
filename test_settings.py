import sys
sys.path.insert(0, '.')

print("Checking settings...")
from backend.config import settings
print(f"OLLAMA_MODEL from settings: '{settings.ollama_model}'")
print(f"OLLAMA_BASE_URL: '{settings.ollama_base_url}'")

print("\nCreating LLM engine...")
from backend.llm_engine import LLMEngine
llm = LLMEngine()
print(f"LLM model: '{llm.model}'")
print(f"LLM chat_url: '{llm._chat_url}'")

print("\n=== DONE ===")