import requests

print("1. Test Ollama tags...")
response = requests.get("http://localhost:11434/api/tags", timeout=5)
print(f"   Models: {[m['name'] for m in response.json().get('models', [])]}")

print("\n2. Test embeddings endpoint...")
response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={"model": "all-MiniLM-L6-v2", "prompt": "Test text"},
    timeout=30
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Embedding length: {len(data.get('embedding', []))}")

print("\n3. Test chat with context...")
response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "qwen2.5:3b",
        "messages": [
            {"role": "user", "content": "Kontext: Das RKI ist das Robert Koch-Institut.\n\nFrage: Was ist das RKI?"}
        ],
        "stream": False
    },
    timeout=60
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Answer: {data.get('message', {}).get('content', '')[:200]}")

print("\n=== DONE ===")