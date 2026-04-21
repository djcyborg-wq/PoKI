import requests
import json

API_BASE = "http://localhost:8000/api"


def test_health():
    print("Teste /api/health...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_chat(question="Was ist das RKI?"):
    print(f"Teste Chat mit: {question}")
    payload = {
        "question": question,
        "top_k": 3
    }
    response = requests.post(f"{API_BASE}/chat", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Antwort: {data.get('answer', 'N/A')[:200]}...")
        print(f"Quellen: {len(data.get('sources', []))}")
        print(f"Zeit: {data.get('query_time_ms', 0)}ms")
    else:
        print(f"Fehler: {response.text}")
    print()


def test_folders():
    print("Teste /api/folders...")
    response = requests.get(f"{API_BASE}/folders")
    print(f"Status: {response.status_code}")
    print(f"Ordner: {response.json()}")
    print()


def test_stats():
    print("Teste /api/stats...")
    response = requests.get(f"{API_BASE}/stats")
    print(f"Status: {response.status_code}")
    print(f"Stats: {response.json()}")
    print()


def test_documents():
    print("Teste /api/documents...")
    response = requests.get(f"{API_BASE}/documents")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Anzahl Dokumente: {data.get('count', 0)}")
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("API Tests")
    print("=" * 50)
    print()
    
    try:
        test_health()
        test_folders()
        test_stats()
        test_documents()
        test_chat()
    except Exception as e:
        print(f"Fehler: {e}")
        print("Stelle sicher, dass der Server laeuft auf http://localhost:8000")