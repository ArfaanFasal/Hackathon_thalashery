"""FastAPI entry point for CivicSafe AI backend."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from civicsafe_brain import ai_service as brain
from models import (
    ChatRequest,
    ChatResponse,
    ClusterSummary,
    ComplaintRequest,
    ComplaintResponse,
    DashboardResponse,
    HistoryRecord,
    MapPoint,
    ReportRequest,
    ReportResponse,
    RouteInputRequest,
    ScamRequest,
    ScamResponse,
    ServiceGuidanceRequest,
    ServiceInfoResponse,
    VoiceResponse,
)
from services import (
    analyze_complaint,
    analyze_scam,
    generate_report,
    get_cluster_summaries,
    get_dashboard_data,
    get_history,
    get_map_data,
    get_record_by_id,
    get_service_info,
    route_input,
    service_guidance,
)

from conversation.orchestrator import process_chat_turn
from conversation.store import init_db, list_messages


app = FastAPI(
    title="CivicSafe AI Backend",
    description="Multilingual Smart Civic Assistant & Scam Shield backend API.",
    version="1.0.0",
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# Enable all origins for hackathon frontend integration.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Basic status endpoint."""
    return {"message": "CivicSafe AI Backend Running"}


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check including chat persistence backend."""
    from conversation.store import storage_backend

    return {
        "status": "ok",
        "chat_storage": storage_backend(),
        "gemini_configured": bool(brain.settings.gemini_api_key),
        "gemini_model": brain.settings.gemini_model,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_turn(payload: ChatRequest) -> ChatResponse:
    """Chat-first civic helpdesk turn (conversational; no raw JSON in assistant_message)."""
    return process_chat_turn(
        session_id=payload.session_id,
        message=payload.message,
        quick_reply_id=payload.quick_reply_id,
    )


@app.get("/api/chat/{session_id}/history")
async def chat_history(session_id: str) -> Dict[str, object]:
    """Recent messages for replay in the UI."""
    return {"session_id": session_id, "messages": list_messages(session_id)}


@app.post("/route-input")
async def route_input_endpoint(payload: RouteInputRequest) -> Dict[str, object]:
    """Unified page-agnostic route for chat-based flows."""
    return route_input(text=payload.text, language=payload.language, mode=payload.mode)


@app.post("/analyze-complaint", response_model=ComplaintResponse)
async def analyze_complaint_endpoint(payload: ComplaintRequest) -> ComplaintResponse:
    """Process complaint input and return structured civic response."""
    return analyze_complaint(payload)


@app.post("/analyze-scam", response_model=ScamResponse)
async def analyze_scam_endpoint(payload: ScamRequest) -> ScamResponse:
    """Analyze suspicious message/URL for scam indicators."""
    return analyze_scam(payload)


@app.get("/service-info/{service_name}", response_model=ServiceInfoResponse)
async def service_info_endpoint(service_name: str) -> ServiceInfoResponse:
    """Return static service template for known government services."""
    return get_service_info(service_name)


@app.post("/service-guidance")
async def service_guidance_endpoint(payload: ServiceGuidanceRequest) -> Dict[str, object]:
    """Provide service steps and documents with lightweight AI-style summary."""
    return service_guidance(payload)


@app.post("/voice-to-text", response_model=VoiceResponse)
async def voice_to_text(file: UploadFile = File(...)) -> VoiceResponse:
    """Transcribe speech with Gemini if available, else return explicit demo mode status."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    filename = file.filename or "voice.webm"
    try:
        converted = brain.transcribe_bytes(filename, data)
        return VoiceResponse(
            converted_text=converted,
            language="auto",
            mode="live",
            provider="gemini",
            detail="Gemini transcription completed successfully.",
        )
    except ValueError as exc:
        return VoiceResponse(
            converted_text=f"Demo mode transcription placeholder for {filename}.",
            language="auto",
            mode="demo",
            provider="fallback",
            detail=str(exc),
        )


@app.get("/dashboard-data", response_model=DashboardResponse)
async def dashboard_data() -> DashboardResponse:
    """Return chart-ready analytics derived from saved records."""
    return get_dashboard_data()


@app.get("/map-data", response_model=list[MapPoint])
async def map_data() -> list[MapPoint]:
    """Return complaint markers usable for map visualizations."""
    return get_map_data()


@app.get("/clusters", response_model=list[ClusterSummary])
async def clusters() -> list[ClusterSummary]:
    """Return complaint cluster summaries."""
    return get_cluster_summaries()


@app.post("/generate-report", response_model=ReportResponse)
async def generate_report_endpoint(payload: ReportRequest) -> ReportResponse:
    """Generate explainable processing report for a saved record."""
    report = generate_report(record_type=payload.record_type, record_id=payload.record_id)
    if not report:
        raise HTTPException(status_code=404, detail="Record not found for given type/id")
    return report


@app.get("/history", response_model=list[HistoryRecord])
async def history(record_type: Optional[str] = Query(default=None, alias="type")) -> list[HistoryRecord]:
    """List saved records; optionally filter by complaint/scam/service."""
    if record_type and record_type not in {"complaint", "scam", "service"}:
        raise HTTPException(status_code=400, detail="Invalid type filter")
    return get_history(record_type=record_type)


@app.get("/history/{record_id}", response_model=HistoryRecord)
async def history_detail(record_id: str) -> HistoryRecord:
    """Fetch one saved record by ID."""
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record
