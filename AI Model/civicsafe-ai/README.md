# CivicSafe AI - Multilingual Smart Civic Assistant & Scam Shield

End-to-end AI subsystem for civic complaint intelligence:
- Multilingual complaint understanding (English, Malayalam, Hindi, mixed)
- Voice-to-text support (browser mic recording + Gemini audio transcription)
- Structured complaint extraction
- Intent classification
- Scam signal detection
- Cluster-key generation for dashboards
- AI transparency report generation (JSON + Markdown)

## 1) Project Structure

```text
civicsafe-ai/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── models.py
│   └── services/
│       ├── __init__.py
│       ├── ai_service.py
│       └── report_service.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── public/
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── styles.css
├── scripts/
│   ├── run_backend.ps1
│   ├── run_frontend.ps1
│   └── sample_requests/
│       ├── analyze.json
│       └── generate_report.json
├── tests/
│   └── test_api.py
├── .env.example
├── requirements.txt
└── README.md
```

## 2) Setup

### Backend setup

```powershell
cd "c:\Users\HP\Desktop\Hackthon\AI Model\civicsafe-ai"
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Optional: set `GEMINI_API_KEY` in `.env` for LLM + transcription support.

### Run backend

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:
- [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend setup and run

```powershell
cd "c:\Users\HP\Desktop\Hackthon\AI Model\civicsafe-ai\frontend"
npm install
npm run dev
```

Frontend app:
- [http://localhost:5173](http://localhost:5173)

## 3) API Usage

### GET /health

Response:

```json
{
  "status": "ok"
}
```

### POST /analyze

Request:

```json
{
  "raw_text": "No water supply in Kakkanad"
}
```

Response shape:

```json
{
  "intent": {
    "intent": "complaint_report",
    "confidence": 0.82
  },
  "structured_data": {
    "issue_type": "Water Shortage",
    "location": "Kakkanad",
    "urgency": "Medium",
    "summary": "No water supply in Kakkanad",
    "category": "Utilities",
    "detected_language": "English",
    "required_department": "Water Authority",
    "priority_tag": "standard",
    "suggested_next_step": "Register municipal complaint ticket.",
    "cluster_key": "utilities_water_shortage_kakkanad"
  },
  "scam_analysis": {
    "scam_detected": false,
    "scam_type": "none",
    "risk_level": "low",
    "recommendation": "No scam indicators found."
  },
  "cluster_info": {
    "cluster_key": "utilities_water_shortage_kakkanad",
    "cluster_ready": true
  },
  "confidence": {
    "overall_confidence": 0.806,
    "intent_confidence": 0.82,
    "structure_confidence": 0.9,
    "scam_confidence": 0.7
  },
  "report_available": true
}
```

### POST /transcribe

- Multipart form with `audio` file
- Uses Gemini audio transcription if `GEMINI_API_KEY` is configured
- Frontend fills the textarea with the transcription for you to edit before analysis

### POST /generate-report

Request includes:
- `raw_text`
- full `analysis` object from `/analyze`

Response includes:
- `json_report`
- `markdown_report`

## 4) Integration Guide (Team Friendly)

- **Arfaan (AI):** extend prompts and fallback rules in `app/services/ai_service.py`
- **Daniya (Backend/DB):** call `/analyze` and persist `structured_data`, `cluster_info`, and confidence fields
- **Adhish (Scam dashboard):** use `scam_analysis` and `cluster_info` for risk and trend dashboards
- **KP (UI/UX):** reuse response cards from `frontend/src/App.jsx` and style with `styles.css`

## 5) Test

```powershell
cd "c:\Users\HP\Desktop\Hackthon\AI Model\civicsafe-ai"
pytest -q
```

## 6) Notes

- AI endpoints work with LLM when API key is set
- Robust fallback logic ensures output is still valid if AI call fails
- Fallback response format matches requested default schema
