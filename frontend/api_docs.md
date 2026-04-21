# VBA Integration API Dokumentation

## Endpoints

### POST /api/chat

Chat-Anfrage an die Dokumentensuche.

**Request:**
```json
{
    "question": "Was ist die Definition von XYZ?",
    "history": [
        {"role": "user", "content": "Vorherige Frage"},
        {"role": "assistant", "content": "Vorherige Antwort"}
    ],
    "top_k": 5,
    "folders": ["E:\\Mario@work\\RKI"]
}
```

**Response:**
```json
{
    "answer": "Die Definition von XYZ lautet...",
    "sources": [
        {
            "file": "dokument1.pdf",
            "folder": "E:\\Mario@work\\RKI",
            "snippet": "...Relevanter Text..."
        }
    ],
    "query_time_ms": 1234
}
```

## VBA Beispiel

```vba
' Referenz: Microsoft WinHTTP Services
Dim http As Object
Set http = CreateObject("WinHttp.WinHttpRequest.5.1")

Dim url As String
url = "http://localhost:8000/api/chat"

Dim payload As String
payload = "{""question"": ""Was ist das RKI?"", ""top_k"": 5}"

http.Open "POST", url, False
http.SetRequestHeader "Content-Type", "application/json"
http.Send payload

If http.Status = 200 Then
    Dim response As String
    response = http.ResponseText
    
    Dim json As Object
    Set json = JsonConverter.ParseJson(response)
    
    Debug.Print "Antwort: " & json("answer")
    Debug.Print "Quellen: " & UBound(json("sources")) + 1
    
    Dim source As Variant
    For Each source In json("sources")
        Debug.Print "  - " & source("file")
    Next
Else
    Debug.Print "Fehler: " & http.Status & " - " & http.ResponseText
End If
```

### GET /api/folders

Liste aller konfigurierten Dokumenten-Ordner.

**Response:**
```json
{
    "folders": [
        {
            "id": "folder_0",
            "path": "E:\\Mario@work\\RKI",
            "enabled": true,
            "document_count": 42,
            "total_chunks": 1500
        }
    ]
}
```

### POST /api/folders

Neuen Ordner hinzufügen.

**Request:**
```json
{
    "path": "E:\\NeuerOrdner",
    "enabled": true
}
```

### GET /api/stats

Statistiken abrufen.

**Response:**
```json
{
    "total_chunks": 5000,
    "folder_counts": {
        "E:\\Mario@work\\RKI": 3000
    },
    "configured_folders": 2
}
```

### POST /api/reindex

Vollständige Neuindizierung starten (asynchron).

**Response:**
```json
{
    "message": "Reindex started"
}
```

### GET /api/health

System-Gesundheitscheck.

**Response:**
```json
{
    "status": "ok",
    "ollama": "connected",
    "vector_store": "ready"
}
```

## Hinweise

- Server muss auf `localhost:8000` laufen (oder konfigurierbar)
- Ollama muss separat gestartet werden
- Für große Antworten: Timeout erhöhen (default 120s)