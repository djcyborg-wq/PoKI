import requests

url = "http://localhost:11434/api/chat"
payload = {
    "model": "qwen2.5:3b",
    "messages": [
        {"role": "user", "content": "Was ist der RKI?"}
    ],
    "stream": False
}

print("Sending request to Ollama with qwen2.5:3b...")
try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")