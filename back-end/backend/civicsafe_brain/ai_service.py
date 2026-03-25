import json
import re
from typing import Any

from google import genai
from google.genai import types

from civicsafe_brain.config import settings
from civicsafe_brain.models import IntentAnalysis, ScamAnalysis, StructuredComplaint


def generate_cluster_key(category: str, issue_type: str, location: str | None) -> str | None:
    normalized = lambda x: re.sub(r"[^a-z0-9]+", "_", x.lower()).strip("_")
    if not issue_type:
        return None
    parts = [normalized(category or "other"), normalized(issue_type or "unknown")]
    if location:
        parts.append(normalized(location))
    return "_".join([x for x in parts if x]) or None


def _fallback_intent(raw_text: str) -> IntentAnalysis:
    text = raw_text.lower()
    if any(x in text for x in ["otp", "fraud", "scam", "phishing", "kyc"]):
        return IntentAnalysis(intent="scam_report", confidence=0.88)
    if any(x in text for x in ["aadhaar", "passport", "pan", "service", "document"]):
        return IntentAnalysis(intent="service_guidance", confidence=0.72)
    if text.strip():
        return IntentAnalysis(intent="complaint_report", confidence=0.81)
    return IntentAnalysis(intent="unknown", confidence=0.25)


def _fallback_structure(raw_text: str) -> StructuredComplaint:
    text = raw_text.lower()
    issue_type = "Unknown"
    category = "Other"
    department = None
    complaint_type = "grievance"
    if any(k in text for k in ["water", "pani", "vellam"]):
        issue_type, category, department = "Water Issue", "Utilities", "Water Authority"
    elif any(k in text for k in ["road", "pothole"]):
        issue_type, category, department = "Road Issue", "Infrastructure", "Public Works Department"
    elif any(k in text for k in ["garbage", "waste"]):
        issue_type, category, department = "Sanitation Issue", "Sanitation", "Municipal Sanitation Department"
    elif any(k in text for k in ["certificate", "aadhaar", "passport", "pan"]):
        issue_type, category, department, complaint_type = "Certificate Request", "Services", "Revenue Department", "certificate_request"

    location_match = re.search(r"\b(?:in|at|near)\s+([a-zA-Z]+)", raw_text)
    location = location_match.group(1) if location_match else None
    detected_language = "Malayalam" if any("\u0d00" <= c <= "\u0d7f" for c in raw_text) else (
        "Hindi" if any("\u0900" <= c <= "\u097f" for c in raw_text) else "English"
    )
    out = StructuredComplaint(
        issue_type=issue_type,
        main_issue=issue_type,
        complaint_type=complaint_type,
        location=location,
        urgency="Medium",
        summary=raw_text.strip() or "Unable to parse complaint",
        category=category,
        detected_language=detected_language,
        required_department=department,
        severity_keywords=[kw for kw in ["urgent", "unsafe", "emergency", "delay"] if kw in text],
        priority_tag="standard" if issue_type != "Unknown" else None,
        suggested_next_step="Register municipal complaint ticket." if issue_type != "Unknown" else None,
    )
    out.cluster_key = generate_cluster_key(out.category, out.issue_type, out.location)
    return out


def _fallback_scam(raw_text: str) -> ScamAnalysis:
    text = raw_text.lower()
    if any(k in text for k in ["otp", "click here", "verify account", "kyc", "prize", "lottery"]):
        return ScamAnalysis(
            scam_detected=True,
            scam_type="phishing",
            risk_level="high",
            recommendation="Do not share personal data. Block sender and report at cybercrime.gov.in.",
        )
    return ScamAnalysis()


def _client() -> Any | None:
    if not settings.gemini_api_key:
        return None
    return genai.Client(api_key=settings.gemini_api_key)


def _ai_json_or_none(prompt: str) -> dict[str, Any] | None:
    client = _client()
    if not client:
        return None
    try:
        res = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"Return strict JSON only, no markdown.\n{prompt}",
            config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        return json.loads((res.text or "{}").strip() or "{}")
    except Exception:
        return None


def analyze_intent(raw_text: str) -> IntentAnalysis:
    data = _ai_json_or_none(
        "Classify intent as complaint_report, scam_report, service_guidance, general_query, unknown. "
        "Return {\"intent\": string, \"confidence\": number}. Text: " + raw_text
    )
    if data and "intent" in data and "confidence" in data:
        return IntentAnalysis(intent=str(data["intent"]), confidence=float(data["confidence"]))
    return _fallback_intent(raw_text)


def structure_complaint(raw_text: str) -> StructuredComplaint:
    data = _ai_json_or_none(
        "Extract keys issue_type, main_issue, complaint_type, category, subcategory, location, urgency, "
        "summary, detected_language, required_department, duration_text, duration_value, duration_unit, "
        "severity_keywords, priority_tag, suggested_next_step, cluster_key from text: " + raw_text
    )
    if data:
        try:
            parsed = StructuredComplaint(**data)
            parsed.cluster_key = generate_cluster_key(parsed.category, parsed.issue_type, parsed.location)
            return parsed
        except Exception:
            pass
    return _fallback_structure(raw_text)


def analyze_scam(raw_text: str) -> ScamAnalysis:
    data = _ai_json_or_none(
        "Detect scam and return {\"scam_detected\": bool, \"scam_type\": str, \"risk_level\": str, "
        "\"recommendation\": str}. Text: " + raw_text
    )
    if data:
        try:
            return ScamAnalysis(**data)
        except Exception:
            pass
    return _fallback_scam(raw_text)


def transcribe_bytes(filename: str, file_bytes: bytes) -> str:
    """Transcribe audio; Malayalam (or other languages) → English text for downstream intent detection."""
    client = _client()
    if not client:
        raise ValueError("GEMINI_API_KEY not configured.")
    ext = filename.lower().split(".")[-1] if "." in filename else "wav"
    mime_map = {"wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4", "ogg": "audio/ogg", "webm": "audio/webm"}
    mime_type = mime_map.get(ext, "audio/webm")
    instruction = (
        "Listen to this audio. Output **only** fluent English text: transcribe and, if the speech is in "
        "Malayalam, Hindi, Tamil, or any other language, translate the meaning into clear natural English. "
        "No preamble, no quotes, no language tags—just the English lines."
    )
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[instruction, types.Part.from_bytes(data=file_bytes, mime_type=mime_type)],
            config={"temperature": 0.0},
        )
        return (response.text or "").strip()
    except Exception as exc:
        raise ValueError(f"Audio transcription failed: {exc}") from exc


def conversational_opening() -> str:
    fallback = (
        "Hello — I'm CivicSafe AI. I'm here to help with civic services, complaints, scam checks, or "
        "general questions about public programmes. What's going on, in your own words?"
    )
    client = _client()
    if not client:
        return fallback
    try:
        res = client.models.generate_content(
            model=settings.gemini_model,
            contents=(
                "You are CivicSafe AI, a civic helpdesk assistant. Write a short opening (2-3 sentences). "
                "Be professional but conversational—like talking to a colleague, not a call-centre script. "
                "Invite the user to explain naturally (services, complaints, safety, data questions). "
                "Do not list numbered options or say 'select one'. Use straight ASCII apostrophes (')."
            ),
            config={"temperature": 0.45},
        )
        return (res.text or "").strip() or fallback
    except Exception:
        return fallback


def conversational_nudge(user_said: str, nudge_type: str) -> str:
    """
    Natural follow-up instead of rigid menus.
    nudge_type: vague | ambiguous_intent | need_area | need_detail | after_intent_locked
    """
    fallback_map = {
        "vague": "I follow you — could you say a bit more about whether this is about getting a service done, reporting a problem, or something that feels risky?",
        "ambiguous_intent": "Thanks. Is this mainly something you want to apply for or get guidance on, or a problem you want logged as a complaint?",
        "need_area": "Sure. Is this closer to everyday services like water or electricity, identity documents like Aadhaar, safety or police-related, or something else you have in mind?",
        "need_detail": "Got it. In a sentence or two, what exactly happened and where—so I can point you to the right next step?",
        "after_intent_locked": "Thanks, that helps. I'll ask just one or two short follow-ups so we can summarise this properly for you.",
        "need_location": "Which city or area should we associate with this—so I can tailor the guidance?",
        "need_urgency": "How urgent would you say this is: low, medium, high, or critical?",
        "need_since": "Roughly when did this start, or how long has it been an issue?",
        "pick_item": "Here are some common labels that might fit—tap the closest one, or describe your own wording.",
    }
    fallback = fallback_map.get(nudge_type, fallback_map["vague"])
    client = _client()
    if not client:
        return fallback
    try:
        res = client.models.generate_content(
            model=settings.gemini_model,
            contents=(
                f"You are CivicSafe AI. The citizen said: \"{user_said[:1200]}\"\n"
                f"Situation: {nudge_type}.\n"
                "Reply in 2-3 short sentences, warm and professional, no bullet menus, no 'option 1 2 3'. "
                "Ask one clear follow-up question if helpful. ASCII apostrophes only."
            ),
            config={"temperature": 0.4},
        )
        return (res.text or "").strip() or fallback
    except Exception:
        return fallback


def polish_assistant_message(draft: str) -> str:
    """Optional Gemini rewrite for conversational tone; no-op if no API key."""
    client = _client()
    if not client or not draft.strip():
        return draft
    try:
        res = client.models.generate_content(
            model=settings.gemini_model,
            contents=(
                "You are CivicSafe AI, a helpful civic helpdesk assistant. "
                "Rewrite the following draft for chat: short paragraphs, clear, empathetic, no JSON, no bullet spam. "
                "Use straight ASCII apostrophes (') only. Keep all factual guidance and disclaimers.\n\nDraft:\n"
                + draft
            ),
            config={"temperature": 0.35},
        )
        return (res.text or draft).strip() or draft
    except Exception:
        return draft
