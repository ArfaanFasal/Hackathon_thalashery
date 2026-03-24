import json
import re
from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.models import IntentAnalysis, ScamAnalysis, StructuredComplaint


def _normalize_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def generate_cluster_key(category: str, issue_type: str, location: str | None) -> str | None:
    if not issue_type:
        return None
    parts = [_normalize_slug(category or "other"), _normalize_slug(issue_type or "unknown")]
    if location:
        parts.append(_normalize_slug(location))
    value = "_".join([p for p in parts if p])
    return value or None


def _fallback_intent(raw_text: str) -> IntentAnalysis:
    text = raw_text.lower()
    scam_terms = ["otp", "phishing", "loan", "aadhaar", "fraud", "scam", "fake website"]
    complaint_terms = ["water", "electricity", "road", "drain", "garbage", "pani", "vellam"]
    if any(t in text for t in scam_terms):
        return IntentAnalysis(intent="scam_report", confidence=0.88)
    if any(t in text for t in complaint_terms):
        return IntentAnalysis(intent="complaint_report", confidence=0.82)
    if "how" in text or "guide" in text:
        return IntentAnalysis(intent="service_guidance", confidence=0.66)
    if text.strip():
        return IntentAnalysis(intent="general_query", confidence=0.55)
    return IntentAnalysis(intent="unknown", confidence=0.25)


def _fallback_structure(raw_text: str) -> StructuredComplaint:
    text = raw_text.lower()
    category = "Other"
    issue_type = "Unknown"
    department = None
    location = None

    match = re.search(r"\b(?:in|at|near)\s+([a-zA-Z]+)", raw_text)
    if match:
        location = match.group(1)

    if any(k in text for k in ["water", "vellam", "pani"]):
        category = "Utilities"
        issue_type = "Water Shortage"
        department = "Water Authority"
    elif any(k in text for k in ["road", "pothole"]):
        category = "Infrastructure"
        issue_type = "Road Damage"
        department = "Public Works Department"
    elif any(k in text for k in ["garbage", "waste"]):
        category = "Sanitation"
        issue_type = "Waste Management"
        department = "Municipal Sanitation Department"

    structured = StructuredComplaint(
        issue_type=issue_type,
        location=location,
        urgency="Medium",
        summary=raw_text.strip() if raw_text.strip() else "Unable to parse complaint",
        category=category,
        detected_language=detect_language(raw_text),
        required_department=department,
        priority_tag="standard" if issue_type != "Unknown" else None,
        suggested_next_step="Register municipal complaint ticket." if issue_type != "Unknown" else None,
        cluster_key=None,
    )
    structured.cluster_key = generate_cluster_key(structured.category, structured.issue_type, structured.location)
    return structured


def detect_language(raw_text: str) -> str:
    malayalam_range = any("\u0d00" <= c <= "\u0d7f" for c in raw_text)
    devanagari_range = any("\u0900" <= c <= "\u097f" for c in raw_text)
    has_latin = bool(re.search(r"[a-zA-Z]", raw_text))
    if malayalam_range and has_latin:
        return "Mixed (Malayalam + English)"
    if devanagari_range and has_latin:
        return "Mixed (Hindi + English)"
    if malayalam_range:
        return "Malayalam"
    if devanagari_range:
        return "Hindi"
    return "English"


def _fallback_scam(raw_text: str) -> ScamAnalysis:
    text = raw_text.lower()
    patterns = {
        "fake_loan": ["instant loan", "processing fee", "loan approved"],
        "phishing": ["link", "verify account", "suspended", "click here"],
        "otp_fraud": ["otp", "share code", "verification code"],
        "fake_website": ["fake website", "lookalike site"],
        "aadhaar_scam": ["aadhaar", "kyc", "update aadhaar"],
    }
    for scam_type, keys in patterns.items():
        if any(k in text for k in keys):
            return ScamAnalysis(
                scam_detected=True,
                scam_type=scam_type,
                risk_level="high" if scam_type in {"otp_fraud", "phishing"} else "medium",
                recommendation="Do not share personal data, block sender, and report to cybercrime portal.",
            )
    return ScamAnalysis()


def _get_model() -> Any | None:
    if not settings.gemini_api_key:
        return None
    return genai.Client(api_key=settings.gemini_api_key)


def _ai_json_or_none(prompt: str) -> dict[str, Any] | None:
    client = _get_model()
    if not client:
        return None
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"Return only valid JSON. No markdown.\n{prompt}",
            config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )
        content = (response.text or "").strip() or "{}"
        return json.loads(content)
    except Exception:
        return None


def analyze_intent(raw_text: str) -> IntentAnalysis:
    prompt = (
        "Classify intent into one of: complaint_report, scam_report, service_guidance, general_query, unknown. "
        "Return JSON: {\"intent\": string, \"confidence\": number}. Text: "
        + raw_text
    )
    data = _ai_json_or_none(prompt)
    if data and "intent" in data and "confidence" in data:
        return IntentAnalysis(intent=data["intent"], confidence=float(data["confidence"]))
    return _fallback_intent(raw_text)


def structure_complaint(raw_text: str) -> StructuredComplaint:
    prompt = (
        "Extract complaint JSON with exactly keys: issue_type, location, urgency, summary, category, "
        "detected_language, required_department, priority_tag, suggested_next_step, cluster_key. "
        "Rules: if missing location null, urgency Medium, category Other. "
        "Text: " + raw_text
    )
    data = _ai_json_or_none(prompt)
    if data:
        try:
            item = StructuredComplaint(**data)
            item.cluster_key = generate_cluster_key(item.category, item.issue_type, item.location)
            return item
        except Exception:
            pass
    return _fallback_structure(raw_text)


def analyze_scam(raw_text: str) -> ScamAnalysis:
    prompt = (
        "Detect scam indicators. Return JSON with keys: scam_detected(boolean), scam_type, risk_level, recommendation. "
        "Types include fake_loan, phishing, otp_fraud, fake_website, aadhaar_scam, none. Text: "
        + raw_text
    )
    data = _ai_json_or_none(prompt)
    if data:
        try:
            return ScamAnalysis(**data)
        except Exception:
            pass
    return _fallback_scam(raw_text)


def transcribe_bytes(filename: str, file_bytes: bytes) -> str:
    client = _get_model()
    if not client:
        raise ValueError("GEMINI_API_KEY not configured. Use browser voice input or set API key.")
    ext = filename.lower().split(".")[-1] if "." in filename else "wav"
    mime_map = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
    }
    mime_type = mime_map.get(ext, "audio/wav")
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                "Transcribe this audio accurately. Return plain text only.",
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
            config={"temperature": 0.0},
        )
        return (response.text or "").strip()
    except Exception as exc:
        raise ValueError(f"Audio transcription failed with Gemini: {exc}") from exc
