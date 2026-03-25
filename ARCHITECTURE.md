# CivicSafe AI — revised architecture (chat-first)

## What was wrong before

- **Form-first UX**: The main flow relied on rigid category dropdowns instead of natural conversation.
- **One-shot routing**: `/route-input` jumped straight to backend handlers without guided clarification for vague intents.
- **Raw JSON in UI**: API responses were surfaced as JSON blobs instead of readable cards and prose.
- **Thin taxonomy**: Categories did not reflect the full civic domains you specified (identity, municipal, law, welfare, etc.).
- **No conversation memory**: There was no session store or multi-turn state machine (stages A–E).
- **Datasets unused in-app**: CSVs under `AI Model/civicsafe-ai/dataset/` were not indexed for retrieval-backed answers.

## Revised architecture

| Layer | Responsibility |
|--------|----------------|
| **Frontend** (`front-end/`) | Dark glassmorphism shell, sidebar nav, **chat-first assistant**, dashboard charts (Recharts), hotspot list. User-facing text and cards only. |
| **API** (`back-end/backend/main.py`) | FastAPI: `/api/chat` orchestrated turns, legacy analytics endpoints, voice STT. |
| **Orchestration** (`conversation/orchestrator.py`) | Stage machine (A–E), quick replies, slot filling, calls into services + retrieval. |
| **Persistence** (`conversation/store.py`) | SQLite: `data/civicsafe_chat.sqlite` for sessions + transcript. |
| **Taxonomy** (`taxonomy.py`) | Domains, services, complaints, keywords for rule routing. |
| **Knowledge** (`knowledge/retrieval.py`) | CSV chunking + token overlap search (hackathon-simple, no vector DB). |
| **AI brain** (`civicsafe_brain/`) | Gemini JSON tasks + fallbacks; optional conversational polish. |
| **Core services** (`services.py`) | Complaint/scam/service analysis, dashboard aggregation, in-memory case history for demo. |

## Folder structure (high level)

```
back-end/backend/
  main.py
  models.py
  services.py
  taxonomy.py
  civicsafe_brain/
  conversation/
    orchestrator.py
    store.py
  knowledge/
    retrieval.py
  data/                    # created at runtime (SQLite)

front-end/src/
  App.jsx
  index.css
  lib/api.js
  components/
    ChatAssistant.jsx
    DashboardHome.jsx
    AnalyticsView.jsx
    RichText.jsx
```

## Conversation stages (internal)

- **A — Understand**: Detect vague vs specific input; offer intent quick replies.
- **B — Parent domain**: Choose civic domain (utilities, identity, etc.).
- **C — Sub-topic**: Pick concrete service or complaint type.
- **D — Slots**: Short questions (location, urgency, timeline).
- **E — Finalize**: Human-readable summary + optional `SummaryCard`; internal calls to `analyze_complaint`, `analyze_scam`, or `service_guidance`; informational path uses dataset retrieval.

## Internal vs user-facing models

- **Internal**: `HistoryRecord`, raw `structured_output` in services, SQLite state JSON.
- **User-facing**: `ChatResponse` with `assistant_message`, `quick_replies`, `summary_card`, `scam_banner` — rendered as prose and cards in React (no JSON dump).

## Dataset ingestion / retrieval (design)

- **Ingest**: On first search, CSV rows are flattened to text chunks with `theme` = parent folder (Law, climate, …).
- **Retrieve**: Token overlap scoring; top snippets passed into informational responses.
- **Production path**: Swap `KnowledgeIndex` for embeddings + `pgvector` / managed vector store; keep the same `search(query)` interface.

## Scam detection

- **Rules**: Keyword/urgency heuristics in `services.analyze_scam` + brain fallbacks.
- **LLM**: Optional Gemini scam JSON when `GEMINI_API_KEY` is set.
- **UI**: `ScamBanner` on risky utterances (OTP/UPI/phishing patterns).

## Removed or avoided (compliance / realism)

- No automated Aadhaar/PAN/passport **submissions**, e-sign, or identity-bound actions.
- No claim of government accreditation or live ticket integration.
- No custom ML training — uses API LLM + rules + retrieval only.

## API quick reference

- `POST /api/chat` — body: `{ session_id?, message?, quick_reply_id? }`
- `GET /api/chat/{session_id}/history` — transcript replay
- `POST /voice-to-text` — multipart `file`
- `GET /dashboard-data`, `GET /map-data`, `GET /history` — dashboard feeds

## Sample conversation flows (manual)

1. **Vague**: “I have an issue with documents” → clarifying quick replies → service → domain → item → slots → guidance card.
2. **Direct complaint**: “Streetlight not working near MG Road Bangalore” → matched municipal complaint → slots → complaint summary card + `record_id`.
3. **Scam**: “They asked for OTP on WhatsApp” → scam banner + risk summary card.
4. **Info**: “Show NSVA for Andhra” → retrieval snippets + knowledge card.

## Testing checklist

- [ ] Backend `uvicorn main:app` starts; `POST /api/chat` with empty body returns greeting.
- [ ] Chat completes a complaint path and increments `/dashboard-data` totals.
- [ ] Scam message shows banner + completes scam summary.
- [ ] Information question returns dataset snippets (if index built from CSV path).
- [ ] Voice upload returns text (with `GEMINI_API_KEY`) or demo placeholder without key.
- [ ] Frontend build passes; Assistant tab shows cards, not raw JSON.

## Optional next steps

- Lazy-load Recharts to shrink bundle.
- Postgres for sessions + cases; retain SQLite for local hackathon.
- Admin view over `history` with filters.
- i18n toggle (detect language + user-selected language).
