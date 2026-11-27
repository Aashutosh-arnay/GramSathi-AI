# GramSathi AI Service

Internal Python + FastAPI service powering two AI modules:

| Module | Endpoint | Status | Purpose |
|---|---|---|---|
| **FarmSathi AI** | `POST /api/v1/farmsathi/chat` | ✅ Phase B (RAG) | Agricultural assistant for Indian farmers |
| **NyayaSathi AI** | `POST /api/v1/nyayasathi/chat` | ✅ Phase C (Legal RAG) | Legal-information assistant for Indian citizens |

> Both modules support **Hindi and English** and are designed to plug into the GramSathi AI Node.js + React platform.

---

## Folder structure

```
ai-service/
├── app/
│   ├── main.py                       # FastAPI app, startup ingestion, prod guard
│   ├── api/
│   │   └── routes/
│   │       ├── health.py             # GET /health
│   │       ├── farmsathi.py          # POST /api/v1/farmsathi/chat
│   │       └── nyayasathi.py         # POST /api/v1/nyayasathi/chat (stub)
│   ├── schemas/
│   │   └── chat_schema.py            # Shared Pydantic request/response/error models
│   ├── services/
│   │   ├── embedding_service.py      # Local sentence-transformers provider
│   │   ├── llm_service.py            # Mock (default) + Gemini provider stub
│   │   └── retrieval_service.py      # Top-k + threshold Chroma retrieval
│   ├── farmsathi/
│   │   ├── knowledge_base.py         # PyMuPDF extraction, cleaning, chunking, Chroma
│   │   ├── ingest.py                 # Standalone CLI ingestion script
│   │   ├── prompts.py                # Grounded system & user prompt builders
│   │   └── service.py                # FarmSathi RAG orchestration
│   └── core/
│       ├── config.py                 # Settings (pydantic-settings, .env)
│       ├── security.py               # Internal API-key auth dependency
│       └── exceptions.py             # Custom exceptions + global handlers
├── tests/
│   ├── conftest.py
│   ├── test_farmsathi.py
│   └── fixtures/
│       └── create_fixtures.py        # Generates TEST PDFs + sidecar JSONs
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

---

## Prerequisites

- Python 3.11+
- pip / pip3

---

## Setup

```bash
# 1. Navigate to ai-service
cd GramSathi-AI/ai-service

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

By default, `.env.example` uses:
- `EMBEDDING_PROVIDER=local` (`paraphrase-multilingual-MiniLM-L12-v2`, no key needed)
- `LLM_PROVIDER=mock` (no API key needed; assembles answers from retrieved chunks)
- `ENV=development` (set `ENV=production` and a strong `AI_SERVICE_API_KEY` before deploying; production refuses to start if `AI_SERVICE_API_KEY` is empty)

---

## Knowledge Base Ingestion (FarmSathi)

Place agricultural PDFs in `FARMSATHI_DATA_PATH` (`../dataset/farmsathi` by default).  
Each PDF **must** have a sibling `<filename>.json` sidecar containing its source metadata:

```json
{
  "source_title": "ICAR Wheat Production Guide",
  "publisher": "ICAR",
  "url": "https://icar.org.in/wheat-guide",
  "topic": "wheat production",
  "language": "en",
  "published_date": "2023-01-15",
  "retrieval_date": "2026-11-26",
  "region": "North India"
}
```

PDFs without a sidecar are skipped with a warning. If the folder is empty or missing, the service still starts and returns `answerStatus: "insufficient_information"`.

To validate your dataset before ingesting, and to ingest or rebuild the collection:

```bash
python scripts/validate_dataset.py
python -m app.farmsathi.ingest --rebuild
```

---

## Knowledge Base Ingestion (NyayaSathi)

Place official legal PDFs in `NYAYASATHI_DATA_PATH` (`../dataset/nyayasathi` by default).  
Each PDF **must** have a sibling `<filename>.json` sidecar with §5.3 metadata:

```json
{
  "document_title": "Consumer Protection Act, 2019",
  "issuing_authority": "Ministry of Law and Justice, Government of India",
  "url": "https://www.indiacode.nic.in/...",
  "jurisdiction": "central",
  "applicable_state": "",
  "act_name": "Consumer Protection Act, 2019",
  "section_number": "Section 35",
  "publication_date": "2019-08-09",
  "effective_date": "2020-07-20",
  "last_updated_date": "2020-07-20",
  "retrieval_date": "2026-11-28",
  "language": "en"
}
```

- `jurisdiction` must be `"central"` or `"state"` (with `applicable_state` set for state laws).
- Retrieval automatically filters to `central` + matching `context.state` (never leaking another state's law).
- Every response includes the localized legal disclaimer (`en` / `hi`).

To run legal ingestion manually (use `--rebuild` to drop and rebuild stale chunks):

```bash
python -m app.nyayasathi.ingest --rebuild
```

---

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service starts at **http://localhost:8000**.

| URL | Description |
|---|---|
| `GET  /health` | Liveness probe |
| `GET  /docs` | Swagger UI (interactive API docs) |
| `GET  /redoc` | ReDoc API docs |
| `GET  /openapi.json` | OpenAPI schema |

---

## Run Tests

```bash
pytest -v
```

Tests automatically generate temporary `TEST` fixture PDFs in `tests/fixtures/` (never touching `dataset/`), use an isolated Chroma directory, and run with `LLM_PROVIDER=mock` and `EMBEDDING_PROVIDER=local`.

---

## Authentication

All `/api/v1/*` endpoints require the shared internal API key in the request header:

```
AI-Service-Api-Key: <value of AI_SERVICE_API_KEY>
```

This key is **separate** from the user JWT managed by the Node.js backend.  
In `ENV=development`, leaving `AI_SERVICE_API_KEY=` empty skips auth. In `ENV=production`, an empty key causes the server to exit on startup.

---

## Switching to Gemini

Set in `.env` (no extra SDK package required; uses `httpx` directly). Both `LLM_API_KEY` and a pinned `LLM_MODEL` are required:

```env
LLM_PROVIDER=gemini
LLM_API_KEY=your-gemini-api-key
LLM_MODEL=gemini-2.0-flash
```
