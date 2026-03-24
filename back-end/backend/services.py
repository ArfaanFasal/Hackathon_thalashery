"""Business logic for CivicSafe AI backend.

This module keeps FastAPI route handlers slim by implementing all processing
steps here: routing, complaint analysis, scam checks, service guidance,
clustering, dashboard aggregation, and explainable report generation.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from models import (
    ClusterSummary,
    ComplaintRequest,
    ComplaintResponse,
    DashboardResponse,
    HistoryRecord,
    MapPoint,
    ReportResponse,
    ScamRequest,
    ScamResponse,
    ServiceGuidanceRequest,
    ServiceInfoResponse,
)


# -----------------------------
# In-memory hackathon storage
# -----------------------------
HISTORY_DB: List[HistoryRecord] = []
REPORT_DB: Dict[str, ReportResponse] = {}


SERVICE_CATALOG: Dict[str, Dict[str, Any]] = {
    "aadhaar": {
        "documents_required": ["Identity proof", "Address proof", "Date of birth proof"],
        "steps": [
            "Visit nearest Aadhaar enrollment or update center.",
            "Fill Aadhaar update/application form.",
            "Submit biometric and demographic details.",
            "Collect acknowledgment slip and track status.",
        ],
        "official_website": "https://uidai.gov.in",
        "support_channel": "UIDAI helpline: 1947",
    },
    "pan": {
        "documents_required": ["Identity proof", "Address proof", "Passport-size photo"],
        "steps": [
            "Open NSDL/UTIITSL PAN application portal.",
            "Fill Form 49A with valid details.",
            "Upload required documents and pay fee.",
            "Track PAN application status online.",
        ],
        "official_website": "https://www.onlineservices.nsdl.com",
        "support_channel": "NSDL support desk",
    },
    "passport": {
        "documents_required": ["Address proof", "Date of birth proof", "Photo ID"],
        "steps": [
            "Register on Passport Seva portal.",
            "Complete passport application form.",
            "Pay fee and book appointment.",
            "Attend PSK appointment and police verification.",
        ],
        "official_website": "https://www.passportindia.gov.in",
        "support_channel": "Passport Seva support center",
    },
    "loan": {
        "documents_required": ["Identity proof", "Income proof", "Bank statements"],
        "steps": [
            "Choose lender and compare rates.",
            "Submit application with KYC and income documents.",
            "Complete verification process.",
            "Review sanction terms before acceptance.",
        ],
        "official_website": "https://www.rbi.org.in",
        "support_channel": "Contact verified bank branch only",
    },
}


LOCATION_COORDS: Dict[str, Tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "kochi": (9.9312, 76.2673),
    "chennai": (13.0827, 80.2707),
    "pune": (18.5204, 73.8567),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "unknown": (20.5937, 78.9629),
}


HINGLISH_NORMALIZATION = {
    "current nahi hai": "no electricity",
    "paani nahi aa raha": "no water",
    "road kharab hai": "damaged road",
}


SCAM_KEYWORDS = {
    "otp": 20,
    "urgent": 10,
    "bank": 12,
    "win": 12,
    "lottery": 15,
    "prize": 12,
    "click": 10,
    "verify": 10,
    "blocked": 8,
    "loan approval": 15,
    "kyc": 10,
}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def detect_language(text: str) -> str:
    """Detect language using simple heuristics for demo purposes."""
    lowered = text.lower()
    devanagari_present = bool(re.search(r"[\u0900-\u097F]", text))
    malayalam_present = bool(re.search(r"[\u0D00-\u0D7F]", text))

    if malayalam_present:
        return "Malayalam"
    if devanagari_present:
        return "Hindi"
    if any(phrase in lowered for phrase in HINGLISH_NORMALIZATION):
        return "Hinglish"
    hindi_roman_clues = ["nahi", "paani", "sadak", "bijli", "kharab", "hai"]
    if sum(1 for token in hindi_roman_clues if token in lowered) >= 2:
        return "Hinglish"
    return "English"


def normalize_hinglish(text: str) -> str:
    """Normalize known Hinglish phrases into plain English."""
    normalized = text.lower()
    for source, target in HINGLISH_NORMALIZATION.items():
        normalized = normalized.replace(source, target)
    return normalized


def mock_translate_to_english(text: str, language: str) -> str:
    """Mock translation step for non-English messages."""
    if language in {"Hindi", "Malayalam"}:
        return f"{text} (translated to English - demo)"
    return text


def classify_issue_type(text: str) -> str:
    """Map complaint text to issue categories via keyword rules."""
    lowered = text.lower()
    rules = {
        "Road Issue": ["road", "pothole", "traffic", "street", "bridge", "damaged road"],
        "Water Issue": ["water", "paani", "leakage", "pipeline", "drain"],
        "Electricity Issue": ["electricity", "power", "current", "transformer", "voltage"],
        "Sanitation Issue": ["garbage", "waste", "sewage", "toilet", "sanitation"],
        "Safety Issue": ["crime", "unsafe", "harassment", "accident", "fire", "injury"],
    }
    for issue, keywords in rules.items():
        if any(word in lowered for word in keywords):
            return issue
    return "Other Issue"


def detect_urgency(text: str) -> str:
    """Classify urgency with simple priority words."""
    lowered = text.lower()
    if any(k in lowered for k in ["accident", "fire", "injury", "emergency"]):
        return "Critical"
    if any(k in lowered for k in ["urgent", "danger", "severe"]):
        return "High"
    if any(k in lowered for k in ["issue", "problem", "not working"]):
        return "Medium"
    return "Low"


def extract_location(text: str) -> str:
    """Extract a location token from text using known city names."""
    lowered = text.lower()
    for city in LOCATION_COORDS:
        if city != "unknown" and city in lowered:
            return city.title()
    return "Unknown"


def infer_intent(text: str) -> str:
    """Detect whether user asks for complaint, scam check, or service guidance."""
    lowered = text.lower()
    if any(k in lowered for k in ["otp", "lottery", "kyc", "click", "scam", "fraud", "prize"]):
        return "scam"
    if any(k in lowered for k in ["aadhaar", "passport", "pan", "loan", "service", "document"]):
        return "service"
    return "complaint"


def _risk_score_from_urgency(urgency: str) -> int:
    return {"Low": 25, "Medium": 45, "High": 70, "Critical": 90}.get(urgency, 30)


def _create_insight(issue_type: str, location: str, urgency: str, cluster_size: int) -> str:
    if issue_type == "Water Issue" and cluster_size > 1:
        return "Repeated water issue pattern detected."
    if urgency in {"High", "Critical"}:
        return "Escalation recommended due to high urgency."
    if location != "Unknown" and cluster_size > 2:
        return "Increasing complaints in this area."
    return "Pattern recorded; monitoring for trend changes."


def _save_record(record_type: str, raw_input: Dict[str, Any], processed_output: Dict[str, Any], record_id: str) -> HistoryRecord:
    record = HistoryRecord(
        id=record_id,
        type=record_type,  # type: ignore[arg-type]
        created_at=_utcnow(),
        raw_input=raw_input,
        processed_output=processed_output,
    )
    HISTORY_DB.append(record)
    return record


def get_history(record_type: Optional[str] = None) -> List[HistoryRecord]:
    if record_type is None:
        return HISTORY_DB
    return [r for r in HISTORY_DB if r.type == record_type]


def get_record_by_id(record_id: str) -> Optional[HistoryRecord]:
    return next((record for record in HISTORY_DB if record.id == record_id), None)


def _cluster_key(issue_type: str, location: str) -> str:
    return f"{issue_type.lower()}::{location.lower()}"


def get_cluster_summaries() -> List[ClusterSummary]:
    complaint_records = [r for r in HISTORY_DB if r.type == "complaint"]
    grouped: Dict[str, List[HistoryRecord]] = defaultdict(list)
    for record in complaint_records:
        output = record.processed_output
        key = _cluster_key(output.get("issue_type", "Other Issue"), output.get("location", "Unknown"))
        grouped[key].append(record)

    summaries: List[ClusterSummary] = []
    for idx, (_, records) in enumerate(grouped.items(), start=1):
        output = records[0].processed_output
        issue_type = output.get("issue_type", "Other Issue")
        location = output.get("location", "Unknown")
        size = len(records)
        insight = _create_insight(issue_type, location, output.get("urgency", "Low"), size)
        summaries.append(
            ClusterSummary(
                cluster_id=f"cluster_{idx}",
                issue_type=issue_type,
                location=location,
                cluster_size=size,
                insight=insight,
            )
        )
    return summaries


def analyze_complaint(payload: ComplaintRequest) -> ComplaintResponse:
    language = detect_language(payload.text) if payload.language == "auto" else payload.language
    normalized = normalize_hinglish(payload.text)
    translated = mock_translate_to_english(normalized, language)
    issue_type = classify_issue_type(translated)
    urgency = detect_urgency(translated)
    location = extract_location(translated)

    current_clusters = get_cluster_summaries()
    existing = next((c for c in current_clusters if c.issue_type == issue_type and c.location == location), None)
    cluster_size = (existing.cluster_size + 1) if existing else 1
    cluster_id = existing.cluster_id if existing else f"cluster_{len(current_clusters) + 1}"

    base_risk = _risk_score_from_urgency(urgency)
    risk_boost = 10 if cluster_size > 2 else 0
    risk_score = min(100, base_risk + risk_boost)

    insight = _create_insight(issue_type, location, urgency, cluster_size)
    confidence = round(0.55 + min(0.4, (risk_score / 250)), 2)

    record_id = _new_id("cmp")
    structured_output = {
        "issue_type": issue_type,
        "urgency": urgency,
        "location": location,
        "cluster_id": cluster_id,
        "cluster_size": cluster_size,
        "risk_score": risk_score,
        "insight": insight,
    }
    record = _save_record(
        record_type="complaint",
        raw_input={"text": payload.text, "language": payload.language, "complaint_mode": payload.complaint_mode},
        processed_output={
            "detected_language": language,
            "normalized_text": normalized,
            "translated_text": translated,
            **structured_output,
        },
        record_id=record_id,
    )

    return ComplaintResponse(
        record_id=record.id,
        created_at=record.created_at,
        detected_language=language,
        normalized_text=normalized,
        translated_text=translated,
        issue_type=issue_type,
        urgency=urgency,
        location=location,
        cluster_id=cluster_id,
        cluster_size=cluster_size,
        risk_score=risk_score,
        insight=insight,
        confidence=confidence,
        structured_output=structured_output,
    )


def analyze_scam(payload: ScamRequest) -> ScamResponse:
    text = payload.text.lower()
    matched = [kw for kw in SCAM_KEYWORDS if kw in text]
    score = sum(SCAM_KEYWORDS[kw] for kw in matched)

    if payload.url:
        parsed = urlparse(payload.url)
        if parsed.scheme not in {"https", "http"}:
            score += 10
        if parsed.scheme == "http":
            score += 8
        if any(x in parsed.netloc for x in ["bit.ly", "tinyurl", "free", "win"]):
            score += 10

    probability = min(100, max(5, score))
    if probability >= 75:
        risk_level = "High"
    elif probability >= 45:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    if matched:
        reason = f"Suspicious markers detected: {', '.join(matched)}."
    else:
        reason = "No strong scam markers detected, but caution is advised."

    insight = "High-risk phishing pattern detected." if probability >= 75 else "No major phishing trend detected."
    confidence = round(0.5 + min(0.45, probability / 200), 2)

    record_id = _new_id("scm")
    structured_output = {
        "scam_probability": probability,
        "risk_level": risk_level,
        "suspicious_keywords": matched,
        "reason": reason,
        "insight": insight,
    }
    record = _save_record(
        record_type="scam",
        raw_input={"text": payload.text, "url": payload.url},
        processed_output=structured_output,
        record_id=record_id,
    )

    return ScamResponse(
        record_id=record.id,
        created_at=record.created_at,
        scam_probability=probability,
        risk_level=risk_level,
        suspicious_keywords=matched,
        reason=reason,
        insight=insight,
        confidence=confidence,
        structured_output=structured_output,
    )


def _detect_service_from_text(text: str) -> str:
    lowered = text.lower()
    for item in SERVICE_CATALOG:
        if item in lowered:
            return item
    return "aadhaar"


def get_service_info(service_name: str) -> ServiceInfoResponse:
    key = service_name.lower()
    if key not in SERVICE_CATALOG:
        key = "aadhaar"
    template = SERVICE_CATALOG[key]
    readiness = (
        f"You can start {key.upper()} process after collecting {len(template['documents_required'])} core documents."
    )
    return ServiceInfoResponse(
        service_name=key,
        documents_required=template["documents_required"],
        steps=template["steps"],
        official_website=template["official_website"],
        support_channel=template["support_channel"],
        readiness_summary=readiness,
    )


def service_guidance(payload: ServiceGuidanceRequest) -> Dict[str, Any]:
    language = detect_language(payload.text) if payload.language == "auto" else payload.language
    normalized = normalize_hinglish(payload.text)
    category = payload.service_category.lower()
    if category == "auto":
        category = _detect_service_from_text(payload.text)

    info = get_service_info(category)
    intent = "service"
    guidance_output = info.model_dump()
    guidance_output["detected_language"] = language
    guidance_output["normalized_text"] = normalized
    guidance_output["intent"] = intent

    record_id = _new_id("svc")
    record = _save_record(
        record_type="service",
        raw_input={"text": payload.text, "language": payload.language, "service_category": payload.service_category},
        processed_output=guidance_output,
        record_id=record_id,
    )
    guidance_output["record_id"] = record.id
    guidance_output["created_at"] = record.created_at.isoformat()
    return guidance_output


def route_input(text: str, language: str = "auto", mode: str = "auto") -> Dict[str, Any]:
    selected_mode = infer_intent(text) if mode == "auto" else mode.lower()
    if selected_mode == "scam":
        result = analyze_scam(ScamRequest(text=text))
        return {"mode": "scam", "response": result.model_dump()}
    if selected_mode == "service":
        result = service_guidance(
            ServiceGuidanceRequest(text=text, language=language, service_category="auto")
        )
        return {"mode": "service", "response": result}
    result = analyze_complaint(
        ComplaintRequest(text=text, language=language, complaint_mode="general")
    )
    return {"mode": "complaint", "response": result.model_dump()}


def get_dashboard_data() -> DashboardResponse:
    complaint_records = [r for r in HISTORY_DB if r.type == "complaint"]
    scam_records = [r for r in HISTORY_DB if r.type == "scam"]
    service_records = [r for r in HISTORY_DB if r.type == "service"]

    issue_counter = Counter(r.processed_output.get("issue_type", "Other Issue") for r in complaint_records)
    location_counter = Counter(r.processed_output.get("location", "Unknown") for r in complaint_records)
    urgency_counter = Counter(r.processed_output.get("urgency", "Low") for r in complaint_records)

    timeline_counter = Counter(r.created_at.date().isoformat() for r in complaint_records)
    timeline = [{"date": d, "count": c} for d, c in sorted(timeline_counter.items())]

    clusters = get_cluster_summaries()
    return DashboardResponse(
        total_complaints=len(complaint_records),
        most_common_issue=issue_counter.most_common(1)[0][0] if issue_counter else "N/A",
        high_urgency_count=urgency_counter.get("High", 0) + urgency_counter.get("Critical", 0),
        complaints_by_type=dict(issue_counter),
        complaints_by_location=dict(location_counter),
        timeline=timeline,
        top_area=location_counter.most_common(1)[0][0] if location_counter else "N/A",
        total_scam_checks=len(scam_records),
        total_service_queries=len(service_records),
        total_clusters=len(clusters),
    )


def get_map_data() -> List[MapPoint]:
    points: List[MapPoint] = []
    for record in HISTORY_DB:
        if record.type != "complaint":
            continue
        location = str(record.processed_output.get("location", "Unknown")).lower()
        lat, lon = LOCATION_COORDS.get(location, LOCATION_COORDS["unknown"])
        points.append(
            MapPoint(
                lat=lat,
                lon=lon,
                issue=str(record.processed_output.get("issue_type", "Other Issue")),
                location=location.title(),
                urgency=str(record.processed_output.get("urgency", "Low")),
            )
        )
    return points


def generate_report(record_type: str, record_id: str) -> Optional[ReportResponse]:
    record = get_record_by_id(record_id)
    if not record or record.type != record_type:
        return None

    raw = record.raw_input
    processed = record.processed_output
    detected_language = processed.get("detected_language", "English")
    normalized_text = processed.get("normalized_text", raw.get("text", ""))
    intent = record.type

    processing_steps = [
        "Received raw user input from frontend.",
        "Applied language detection and text normalization rules.",
        "Executed intent-specific rule-based analysis pipeline.",
        "Generated structured output with scores and insights.",
        "Saved record to in-memory demo storage.",
    ]
    reasoning_summary = (
        "The output is generated using deterministic keyword and heuristic rules tuned for hackathon demo reliability."
    )
    confidence_summary = (
        "Confidence is estimated from rule coverage (keyword matches, urgency markers, and consistency checks)."
    )

    markdown_report = "\n".join(
        [
            f"# CivicSafe AI Processing Report",
            "",
            f"- **Record ID:** {record.id}",
            f"- **Record Type:** {record.type}",
            f"- **Created At:** {record.created_at.isoformat()}",
            "",
            "## Raw Input",
            f"```json\n{raw}\n```",
            "",
            "## Processing Summary",
            f"- Detected Language: {detected_language}",
            f"- Normalized Text: {normalized_text}",
            f"- Inferred Intent: {intent}",
            "",
            "## Structured Output",
            f"```json\n{processed}\n```",
            "",
            "## Reasoning",
            reasoning_summary,
            "",
            "## Confidence",
            confidence_summary,
        ]
    )

    report = ReportResponse(
        record_id=record.id,
        record_type=record.type,
        raw_input=raw,
        detected_language=str(detected_language),
        normalized_text=str(normalized_text),
        intent=str(intent),
        structured_output=processed,
        processing_steps=processing_steps,
        reasoning_summary=reasoning_summary,
        confidence_summary=confidence_summary,
        markdown_report=markdown_report,
    )
    REPORT_DB[record.id] = report
    return report
