from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    ClusterInfo,
    ConfidenceInfo,
    ReportRequest,
    ReportResponse,
    StructuredComplaint,
    TranscribeResponse,
)
from app.services.ai_service import analyze_intent, analyze_scam, structure_complaint, transcribe_bytes
from app.services.report_service import build_json_report, build_markdown_report


app = FastAPI(title="CivicSafe AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_structure(structured: StructuredComplaint | None) -> StructuredComplaint:
    if structured:
        return structured
    return StructuredComplaint()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    raw_text = payload.raw_text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="raw_text must not be empty")

    try:
        intent = analyze_intent(raw_text)
        structured = _safe_structure(structure_complaint(raw_text))
        scam = analyze_scam(raw_text)
    except Exception:
        intent = analyze_intent("")
        structured = StructuredComplaint()
        scam = analyze_scam("")

    cluster_info = ClusterInfo(cluster_key=structured.cluster_key, cluster_ready=bool(structured.cluster_key))
    structure_confidence = 0.9 if structured.issue_type != "Unknown" else 0.5
    scam_confidence = 0.9 if scam.scam_detected else 0.7
    overall = round((intent.confidence + structure_confidence + scam_confidence) / 3, 3)
    confidence = ConfidenceInfo(
        overall_confidence=overall,
        intent_confidence=float(intent.confidence),
        structure_confidence=structure_confidence,
        scam_confidence=scam_confidence,
    )

    return AnalyzeResponse(
        intent=intent,
        structured_data=structured,
        scam_analysis=scam,
        cluster_info=cluster_info,
        confidence=confidence,
        report_available=True,
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)) -> TranscribeResponse:
    file_bytes = await audio.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    try:
        text = transcribe_bytes(audio.filename or "audio.wav", file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    return TranscribeResponse(text=text)


@app.post("/generate-report", response_model=ReportResponse)
def generate_report(payload: ReportRequest) -> ReportResponse:
    json_report = build_json_report(payload.raw_text, payload.analysis)
    markdown_report = build_markdown_report(json_report)
    return ReportResponse(json_report=json_report, markdown_report=markdown_report)
