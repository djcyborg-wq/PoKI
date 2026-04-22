# PoKI - Private KI Dokumentassistent

Lokale KI-gestützte Dokumentensuche mit Ollama. Durchsucht PDF, DOCX und andere Dokumente mittels semantischer Suche und beantwortet Fragen basierend auf dem Dokumenteninhalt.

## Features

- **Multi-Folder Support**: Mehrere Dokumenten-Ordner konfigurierbar
- **RAG (Retrieval Augmented Generation)**: Semantische Suche + LLM
- **Lokale Modelle**: Ollama Integration (qwen2.5, llama3, etc.)
- **Vector Store**: ChromaDB für Embeddings
- **File Watcher**: Automatische Indizierung bei Änderungen
- **REST API**: Für Integration in andere Anwendungen (VBA, etc.)
- **Web UI**: Chat-Oberfläche mit Ordner-Filter

## Voraussetzungen

- Python 3.10+
- [Ollama](https://ollama.ai)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (optional, für Bild-OCR)

## Schnellstart

```bash
# 1. Klonen
git clone https://github.com/djcyborg-wq/PoKI.git
cd PoKI

# 2. Virtual Environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Ollama starten (separates Terminal)
ollama serve

# 5. Modell laden
ollama pull qwen2.5:3b

# 6. Konfiguration
copy .env.example .env
# .env editieren: DOCUMENT_FOLDERS=Pfad\zu\deinen\Dokumenten

# 7. Indizieren
python scripts/init_index.py

# 8. Server starten
python -m backend.main

# 9. Öffnen: http://localhost:8000
```

## Konfiguration (.env)

```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_EMBEDDING_MODEL=all-MiniLM-L6-v2
OLLAMA_TIMEOUT=300

# Dokumenten-Ordner (kommasepariert)
DOCUMENT_FOLDERS=E:\Dokumente,R:\Archiv

# Vector Store
VECTOR_STORE_PATH=./data/chroma_db

# Text Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_BATCH_SIZE=32

# OCR (optional)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
ENABLE_OCR=false

# File Watcher
ENABLE_FILE_WATCHER=true
DEBOUNCE_SECONDS=3

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|--------|-------------|
| `GET /` | | Web UI |
| `GET /api/health` | | System-Status |
| `POST /api/chat` | | Chat-Anfrage |
| `GET /api/folders` | | Ordner-Liste |
| `POST /api/folders` | | Ordner hinzufügen |
| `DELETE /api/folders/{id}` | | Ordner entfernen |
| `GET /api/stats` | | Statistiken |
| `GET /api/documents` | | Dokumenten-Liste |
| `POST /api/reindex` | | Neuindizierung |

### Chat API

```bash
POST /api/chat
Content-Type: application/json

{
  "question": "Was ist der Inhalt von Dokument X?",
  "top_k": 5,
  "folders": ["ordner1", "ordner2"]  // optional
}
```

Response:
```json
{
  "answer": "Das Dokument beschreibt...",
  "sources": [
    {"file": "dokument.pdf", "folder": "Dokumente", "snippet": "..."}
  ],
  "query_time_ms": 1234
}
```

### Ordner API

```bash
# Liste
GET /api/folders

# Hinzufügen
POST /api/folders
{"path": "E:\\NeuerOrdner", "enabled": true}

# Entfernen
DELETE /api/folders/folder_0?delete_index=true
```

## Projektstruktur

```
PoKI/
├── backend/
│   ├── main.py          # FastAPI App
│   ├── config.py        # Konfiguration
│   ├── document_loader.py
│   ├── text_processor.py
│   ├── vector_store.py
│   ├── llm_engine.py
│   ├── metadata_db.py
│   └── file_watcher.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── api_docs.md     # VBA-Dokumentation
├── scripts/
│   ├── init_index.py
│   ├── reindex.py
│   └── test_api.py
├── data/
│   ├── chroma_db/      # Embeddings
│   └── metadata.db     # SQLite
├── .env.example
├── requirements.txt
└── README.md
```

## VBA Integration

Siehe `frontend/api_docs.md` für VBA-Code-Beispiele.

## Lizenz

MIT License