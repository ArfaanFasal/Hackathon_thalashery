import json
import re
from io import BytesIO
from typing import Any, Optional, Tuple

from openai import OpenAI

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
    text = raw_text.lower().strip()
    if any(x in text for x in ["otp", "fraud", "scam", "phishing", "kyc"]):
        return IntentAnalysis(intent="scam_report", confidence=0.88)
    if any(x in text for x in ["aadhaar", "passport", "pan", "service", "document"]):
        return IntentAnalysis(intent="service_guidance", confidence=0.72)
    # Short greetings / acknowledgements must not default to complaint (breaks chat routing).
    if len(text) <= 24 and re.match(
        r"^(hi|hello|hey|hii|namaste|good morning|good evening|ok|okay|thanks|thank you|thx|bye)\b",
        text,
    ):
        return IntentAnalysis(intent="general_query", confidence=0.86)
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


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


_FREE_CHAT_SYSTEM = (
    "You are CivicSafe AI, a civic helpdesk assistant for India. Write semi-formal, warm, concise English.\n"
    "Return JSON only with keys: reply (string, what the user reads; no markdown), "
    "keywords (array of up to 8 short tokens: e.g. water, thrissur, garbage, certificate), "
    'civic_signal ("none"|"complaint"|"request"|"query"|"follow_up"|"emergency"), '
    "enter_civic_flow (boolean).\n"
    "enter_civic_flow is true only if the user is clearly reporting a civic problem, applying for a service, "
    "asking how to file or track a complaint, or describing danger/urgent infrastructure failure. "
    "It must be false for greetings, thanks, vague chat, or when intent is unclear.\n"
    "civic_signal none for pure greetings/small talk."
)


def _heuristic_free_chat(text: str) -> dict[str, Any]:
    low = text.lower().strip()
    words = re.findall(r"[a-z0-9]+", low)
    keywords = list(dict.fromkeys(words))[:8]
    if len(low) < 36 and re.match(r"^(hi|hello|hey|hii|namaste|good morning|good evening)\b", low):
        return {
            "reply": "Hello — I'm CivicSafe AI. Tell me in your own words if you need help with a service, a civic complaint, or general information.",
            "keywords": [],
            "civic_signal": "none",
            "enter_civic_flow": False,
        }
    civic_kw = (
        "no water",
        "water supply",
        "garbage",
        "drainage",
        "electricity",
        "power cut",
        "street light",
        "pothole",
        "certificate",
        "apply for",
        "passport",
        "aadhaar",
        "complaint",
        "grievance",
        "municipal",
        "ward",
    )
    hit = any(k in low for k in civic_kw)
    if hit:
        sig = "complaint" if any(x in low for x in ("no water", "not collected", "broken", "leak", "overflow", "pothole", "cut")) else "request"
        if any(x in low for x in ("certificate", "apply", "passport", "aadhaar", "connection")):
            sig = "request"
        return {
            "reply": "Thanks for sharing that — I can help you route this. One moment while I line up the right civic steps.",
            "keywords": keywords,
            "civic_signal": sig,
            "enter_civic_flow": True,
        }
    return {
        "reply": "I'm here to help with civic services and complaints. Could you describe what you need in a sentence or two?",
        "keywords": keywords,
        "civic_signal": "none",
        "enter_civic_flow": False,
    }


def free_chat_turn_json(text: str) -> dict[str, Any]:
    """Conversational reply + keywords + whether to open structured civic routing."""
    raw = (text or "").strip()
    if not raw:
        return {
            "reply": "Please type a short message so I can help.",
            "keywords": [],
            "civic_signal": "none",
            "enter_civic_flow": False,
        }
    client = _client()
    if not client:
        return _heuristic_free_chat(raw)
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _FREE_CHAT_SYSTEM},
                {"role": "user", "content": raw},
            ],
            response_format={"type": "json_object"},
            temperature=0.35,
            max_tokens=400,
        )
        data = json.loads((res.choices[0].message.content or "{}").strip() or "{}")
        reply = str(data.get("reply") or "").strip()
        if not reply:
            return _heuristic_free_chat(raw)
        keywords = data.get("keywords")
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k).strip().lower() for k in keywords if str(k).strip()][:8]
        civic_signal = str(data.get("civic_signal") or "none").lower()
        if civic_signal not in ("none", "complaint", "request", "query", "follow_up", "emergency"):
            civic_signal = "none"
        enter = bool(data.get("enter_civic_flow"))
        return {
            "reply": reply,
            "keywords": keywords,
            "civic_signal": civic_signal,
            "enter_civic_flow": enter,
        }
    except Exception:
        return _heuristic_free_chat(raw)


def free_chat_opening() -> str:
    """Semi-formal first message when session starts (no case-status card)."""
    if settings.fast_opening:
        return (
            "Hello — I'm CivicSafe AI. I'm here for a natural chat about civic services, complaints, or safety. "
            "What would you like help with today?"
        )
    client = _client()
    if not client:
        return (
            "Hello — I'm CivicSafe AI. I'm here for a natural chat about civic services, complaints, or safety. "
            "What would you like help with today?"
        )
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write 2 short sentences: semi-formal greeting for a civic helpdesk chatbot. "
                        "Invite the user to describe their issue or question in plain language. No bullet points."
                    ),
                },
            ],
            temperature=0.45,
            max_tokens=120,
        )
        out = (res.choices[0].message.content or "").strip()
        if out:
            return out
        return (
            "Hello — I'm CivicSafe AI. I'm here for a natural chat about civic services, complaints, or safety. "
            "What would you like help with today?"
        )
    except Exception:
        return (
            "Hello — I'm CivicSafe AI. I'm here for a natural chat about civic services, complaints, or safety. "
            "What would you like help with today?"
        )


def _ai_json_or_none(prompt: str) -> dict[str, Any] | None:
    client = _client()
    if not client:
        return None
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You reply with strict JSON only, no markdown or code fences.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=900,
        )
        text = (res.choices[0].message.content or "").strip()
        return json.loads(text or "{}")
    except Exception:
        return None


def analyze_intent(raw_text: str) -> IntentAnalysis:
    data = _ai_json_or_none(
        "Classify intent as complaint_report, scam_report, service_guidance, general_query, unknown. "
        'Return JSON with keys "intent" (string) and "confidence" (number). Text: ' + raw_text
    )
    if data and "intent" in data and "confidence" in data:
        return IntentAnalysis(intent=str(data["intent"]), confidence=float(data["confidence"]))
    return _fallback_intent(raw_text)


def structure_complaint(raw_text: str) -> StructuredComplaint:
    data = _ai_json_or_none(
        "Extract keys issue_type, main_issue, complaint_type, category, subcategory, location, urgency, "
        "summary, detected_language, required_department, duration_text, duration_value, duration_unit, "
        "severity_keywords, priority_tag, suggested_next_step, cluster_key from text and return one JSON object. Text: "
        + raw_text
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
        'Detect scam and return JSON: {"scam_detected": bool, "scam_type": str, "risk_level": str, '
        '"recommendation": str}. Text: '
        + raw_text
    )
    if data:
        try:
            return ScamAnalysis(**data)
        except Exception:
            pass
    return _fallback_scam(raw_text)


def transcribe_bytes(filename: str, file_bytes: bytes) -> str:
    """Transcribe audio (Whisper). Optional second pass translates to English when TRANSCRIBE_TRANSLATE=1."""
    text, _lang = transcribe_bytes_with_language(filename, file_bytes)
    return text


def transcribe_bytes_with_language(filename: str, file_bytes: bytes) -> Tuple[str, Optional[str]]:
    """Whisper-1 with verbose_json for detected language; optional translate pass to English."""
    client = _client()
    if not client:
        raise ValueError(
            "OPENAI_API_KEY not configured. Add it to back-end/backend/.env and restart the API server."
        )
    name = filename or "voice.webm"
    buf = BytesIO(file_bytes)
    buf.seek(0)
    buf.name = name
    try:
        tr = client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            response_format="verbose_json",
        )
    except Exception as exc:
        raise ValueError(f"Audio transcription failed: {exc}") from exc
    raw = ""
    detected: Optional[str] = None
    if isinstance(tr, dict):
        raw = (tr.get("text") or "").strip()
        detected = tr.get("language")
    else:
        raw = (getattr(tr, "text", None) or "").strip()
        detected = getattr(tr, "language", None)
    if not raw:
        return "", detected
    if not settings.transcribe_translate:
        return raw, detected
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "The following is a speech transcript. It may be Malayalam, Hindi, Tamil, other languages, "
                        "or English. Output only fluent natural English (transcribe and translate if needed). "
                        "No preamble or quotes.\n\n"
                        + raw
                    ),
                },
            ],
            temperature=0.0,
            max_tokens=500,
        )
        out = (res.choices[0].message.content or "").strip()
        return (out or raw), detected
    except Exception:
        return raw, detected


def conversational_opening() -> str:
    fallback = (
        "Hello — I'm CivicSafe AI. I'm here to help with civic services, complaints, scam checks, or "
        "general questions about public programmes. What's going on, in your own words?"
    )
    client = _client()
    if not client:
        return fallback
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are CivicSafe AI, a civic helpdesk assistant. Write a short opening (2-3 sentences). "
                        "Be professional but conversational—like talking to a colleague, not a call-centre script. "
                        "Invite the user to explain naturally (services, complaints, safety, data questions). "
                        "Do not list numbered options or say 'select one'. Use straight ASCII apostrophes (')."
                    ),
                },
            ],
            temperature=0.45,
            max_tokens=180,
        )
        return (res.choices[0].message.content or "").strip() or fallback
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
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"You are CivicSafe AI. The citizen said: \"{user_said[:1200]}\"\n"
                        f"Situation: {nudge_type}.\n"
                        "Reply in 2-3 short sentences, warm and professional, no bullet menus, no 'option 1 2 3'. "
                        "Ask one clear follow-up question if helpful. ASCII apostrophes only."
                    ),
                },
            ],
            temperature=0.4,
            max_tokens=220,
        )
        return (res.choices[0].message.content or "").strip() or fallback
    except Exception:
        return fallback


def polish_assistant_message(draft: str) -> str:
    """Optional OpenAI rewrite for conversational tone; no-op if no API key or CIVIC_POLISH=0."""
    if not settings.polish_chat:
        return draft
    client = _client()
    if not client or not draft.strip():
        return draft
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are CivicSafe AI, a helpful civic helpdesk assistant. "
                        "Rewrite the following draft for chat: short paragraphs, clear, empathetic, no JSON, no bullet spam. "
                        "Use straight ASCII apostrophes (') only. Keep all factual guidance and disclaimers.\n\nDraft:\n"
                        + draft
                    ),
                },
            ],
            temperature=0.35,
            max_tokens=700,
        )
        return (res.choices[0].message.content or draft).strip() or draft
    except Exception:
        return draft
