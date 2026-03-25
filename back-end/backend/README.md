# CivicSafe AI Backend

FastAPI backend for **CivicSafe AI - Multilingual Smart Civic Assistant & Scam Shield**.

This backend is designed for hackathon speed with:
- clean modular structure
- rule-based AI simulation (no heavy ML models)
- chat-friendly unified routing
- page-specific APIs for complaint, scam, service guidance, insights, reports, and history

## Project Structure

```text
backend/
├── main.py
├── models.py
├── services.py
├── requirements.txt
└── README.md
```

## Features

- Complaint Assistant processing (language detect, normalization, classification, urgency, clustering)
- Scam analysis with weighted keyword risk scoring
- Service guidance templates (Aadhaar, PAN, Passport, Loan)
- Unified routing endpoint for chat-style frontend UX
- Dashboard analytics + map markers + cluster summaries
- Explainable AI processing report generation (JSON + Markdown)
- In-memory record history for hackathon demo

## Setup

Chat storage defaults to SQLite for local development.
If you want MongoDB-backed chat persistence, set:

```bash
CHAT_STORAGE=mongodb
```

### 1) Create virtual environment

```bash
python -m venv venv
```

### 2) Activate virtual environment

Linux/macOS:

```bash
source venv/bin/activate
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Run backend

```bash
uvicorn main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`

Windows / Python 3.14 note:

If `--reload` fails with `PermissionError: [WinError 5] Access is denied`, run without reload instead:

```bash
python run_server.py
```

Interactive docs:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

- `GET /` -> backend running message
- `GET /health` -> health status
- `POST /route-input` -> unified intent routing
- `POST /analyze-complaint` -> complaint analysis
- `POST /analyze-scam` -> scam risk analysis
- `GET /service-info/{service_name}` -> static service template
- `POST /service-guidance` -> service help response
- `POST /voice-to-text` -> mock transcription
- `GET /dashboard-data` -> analytics data
- `GET /map-data` -> complaint map markers
- `GET /clusters` -> complaint cluster summaries
- `POST /generate-report` -> explainable processing report
- `GET /history` -> all history (optional `?type=complaint|scam|service`)
- `GET /history/{record_id}` -> single record fetch

## Sample Requests

### Health

```bash
curl http://127.0.0.1:8000/health
```

### Unified route input

```bash
curl -X POST http://127.0.0.1:8000/route-input \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My area in Delhi has road kharab hai and urgent fix needed",
    "language": "auto",
    "mode": "auto"
  }'
```

### Complaint analysis

```bash
curl -X POST http://127.0.0.1:8000/analyze-complaint \
  -H "Content-Type: application/json" \
  -d '{
    "text": "paani nahi aa raha in Mumbai since morning",
    "language": "auto",
    "complaint_mode": "general"
  }'
```

### Scam check

```bash
curl -X POST http://127.0.0.1:8000/analyze-scam \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Urgent! Verify bank OTP to avoid account blocked and win prize",
    "url": "http://bit.ly/verify-now"
  }'
```

### Service guidance

```bash
curl -X POST http://127.0.0.1:8000/service-guidance \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I need documents for passport application",
    "language": "auto",
    "service_category": "auto"
  }'
```

### Generate processing report

```bash
curl -X POST http://127.0.0.1:8000/generate-report \
  -H "Content-Type: application/json" \
  -d '{
    "record_type": "complaint",
    "record_id": "cmp_xxxxx"
  }'
```

## Frontend Integration Notes (Streamlit/React)

- Use `POST /route-input` for GPT-style chat flow when mode is unknown.
- Use page-specific endpoints for side-panel structured data rendering.
- Save IDs returned from analysis endpoints and use them for:
  - report generation via `/generate-report`
  - detail retrieval via `/history/{record_id}`
- Enable API base URL in frontend config, for example:
  - `http://127.0.0.1:8000`

## Report Generation (AI Processing Report)

`POST /generate-report` returns:
- structured report JSON fields
- human-readable `markdown_report`

Report explains:
- raw input
- detected language
- normalized text
- inferred intent
- structured output
- processing steps
- reasoning and confidence summaries

## Data Flow Overview

1. Frontend sends text/voice payload.
2. Backend detects intent and routes analysis.
3. Rule-based processors generate structured output and scores.
4. Records are stored in in-memory history.
5. Dashboard/cluster/map endpoints aggregate stored data.
6. Report endpoint transforms stored records into explainable technical + user-readable report content.

## Hackathon Limitations

- In-memory storage resets when server restarts.
- Language detection, translation, and clustering are heuristic/rule-based.
- Voice-to-text is mocked (no heavy ASR model).
- Scam scoring is keyword weighted and should not be used as legal or production fraud detection.
