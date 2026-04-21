import requests

print("Testing /api/chat through backend...")
try:
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={"question": "Was ist der RKI?", "top_k": 2},
        timeout=120
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Answer: {data.get('answer', 'N/A')[:300]}...")
    else:
        print(f"Error: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")