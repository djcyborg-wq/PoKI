import sys
sys.path.insert(0, '.')

print("1. Testing imports...")
try:
    from backend.config import settings
    print("   config.py OK")
except Exception as e:
    print(f"   config.py ERROR: {e}")
    sys.exit(1)

print(f"\n2. Config values:")
print(f"   OLLAMA_MODEL: {settings.ollama_model}")
print(f"   OLLAMA_BASE_URL: {settings.ollama_base_url}")
print(f"   ENABLE_OCR: {settings.enable_ocr}")
print(f"   DOCUMENT_FOLDERS: {settings.document_folders}")

print("\n3. Testing Ollama connection...")
try:
    import requests
    response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
    print(f"   Ollama status: {response.status_code}")
    if response.status_code == 200:
        models = response.json().get('models', [])
        model_names = [m['name'] for m in models]
        print(f"   Available models: {model_names}")
except Exception as e:
    print(f"   Ollama ERROR: {e}")

print("\n4. Testing LLM Engine...")
try:
    from backend.llm_engine import LLMEngine
    llm = LLMEngine()
    print(f"   Model: {llm.model}")
    print(f"   Chat URL: {llm._chat_url}")
    
    if llm.is_available():
        print("   Ollama is_available: True")
    else:
        print("   Ollama is_available: False")
except Exception as e:
    print(f"   LLM Engine ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n5. Testing Vector Store...")
try:
    from backend.vector_store import VectorStore
    store = VectorStore()
    store.initialize()
    print(f"   Collection: {store.collection.name}")
    stats = store.get_stats()
    print(f"   Stats: {stats}")
except Exception as e:
    print(f"   Vector Store ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n6. Testing Chat with simple query...")
try:
    from backend.vector_store import get_vector_store
    from backend.llm_engine import get_llm_engine
    
    store = get_vector_store()
    store.initialize()
    
    results = store.search("RKI Krisenstab", top_k=2)
    print(f"   Search results: {len(results)}")
    
    if results:
        context = results[0]['content'][:200]
        print(f"   First result: {context}...")
        
        llm = get_llm_engine()
        answer = llm.chat("Was ist der RKI?", context)
        print(f"   Answer: {answer[:200]}...")
    else:
        print("   No search results")
except Exception as e:
    print(f"   Chat test ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n7. Testing Document Loader...")
try:
    from backend.document_loader import DocumentLoader
    loader = DocumentLoader()
    print(f"   Supported extensions: {loader.SUPPORTED_EXTENSIONS if hasattr(loader, 'SUPPORTED_EXTENSIONS') else 'N/A'}")
    
    from backend.document_loader import SUPPORTED_EXTENSIONS
    print(f"   SUPPORTED_EXTENSIONS: {SUPPORTED_EXTENSIONS}")
except Exception as e:
    print(f"   Document Loader ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")