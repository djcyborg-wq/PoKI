import requests
import sys
sys.path.insert(0, '.')

print("1. Test /api/health...")
try:
    response = requests.get("http://localhost:8000/api/health", timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

print("\n2. Test /api/folders...")
try:
    response = requests.get("http://localhost:8000/api/folders", timeout=10)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Folders: {len(data.get('folders', []))}")
except Exception as e:
    print(f"   Error: {e}")

print("\n3. Test /api/stats...")
try:
    response = requests.get("http://localhost:8000/api/stats", timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Stats: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

print("\n4. Test /api/chat...")
try:
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={"question": "Was ist der RKI?", "top_k": 2},
        timeout=120
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Answer: {data.get('answer', 'N/A')[:200]}...")
        print(f"   Sources: {len(data.get('sources', []))}")
    else:
        print(f"   Error: {response.text[:500]}")
except Exception as e:
    print(f"   Error: {e}")

print("\n=== DONE ===")