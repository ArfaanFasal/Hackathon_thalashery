"""Business logic for CivicSafe AI backend."""

from __future__ import annotations

import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from civicsafe_brain import ai_service as brain
from civicsafe_records.store import fetch_all_records, init_records_db, persist_record
from taxonomy import get_item_detail
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


HISTORY_DB: List[HistoryRecord] = []
REPORT_DB: Dict[str, ReportResponse] = {}

SERVICE_CATALOG: Dict[str, Dict[str, Any]] = {
    "aadhaar": {
        "documents_required": ["Identity proof", "Address proof", "Date of birth proof"],
        "steps": [
            "Visit the nearest Aadhaar enrollment or update center.",
            "Fill the Aadhaar update or application form.",
            "Submit biometric and demographic details.",
            "Collect the acknowledgment slip and track status online.",
        ],
        "official_website": "https://uidai.gov.in",
        "support_channel": "UIDAI helpline: 1947",
    },
    "pan": {
        "documents_required": ["Identity proof", "Address proof", "Passport-size photo"],
        "steps": [
            "Open the NSDL or UTIITSL PAN application portal.",
            "Fill Form 49A with valid details.",
            "Upload required documents and pay the fee.",
            "Track the PAN application status online.",
        ],
        "official_website": "https://www.onlineservices.nsdl.com",
        "support_channel": "NSDL support desk",
    },
    "passport": {
        "documents_required": ["Address proof", "Date of birth proof", "Photo ID"],
        "steps": [
            "Register on the Passport Seva portal.",
            "Complete the passport application form.",
            "Pay the fee and book the appointment.",
            "Attend the PSK appointment and police verification.",
        ],
        "official_website": "https://www.passportindia.gov.in",
        "support_channel": "Passport Seva support center",
    },
    "loan": {
        "documents_required": ["Identity proof", "Income proof", "Bank statements"],
        "steps": [
            "Choose a lender and compare rates.",
            "Submit the application with KYC and income documents.",
            "Complete the verification process.",
            "Review sanction terms before acceptance.",
        ],
        "official_website": "https://www.rbi.org.in",
        "support_channel": "Contact a verified bank branch only",
    },
    "water_connection": {
        "documents_required": ["Identity proof", "Address proof", "Property tax receipt or ownership proof", "Passport photos"],
        "steps": [
            "Visit your municipal corporation / water authority office or its online portal.",
            "Submit the new water connection application with site address and plot details.",
            "Pay prescribed fees and schedule inspection if required.",
            "Track application status with the acknowledgement number.",
        ],
        "official_website": "https://kerala.gov.in",
        "support_channel": "Local body water wing / KWA helpline (verify on official site)",
    },
    "electricity_connection": {
        "documents_required": ["Identity proof", "Address proof", "Wiring completion certificate (if applicable)", "Load sanction documents"],
        "steps": [
            "Apply via the state electricity board (e.g. KSEB) online portal or section office.",
            "Submit load details, wiring safety certificate, and identity/address proof.",
            "Pay security deposit and charges as per tariff.",
            "Meter installation is scheduled after technical approval.",
        ],
        "official_website": "https://www.kseb.in",
        "support_channel": "KSEB customer care (verify current number on official portal)",
    },
    "waste_management": {
        "documents_required": ["Address proof", "Property ID / tax number if required locally"],
        "steps": [
            "Register with the municipal sanitation / solid waste management desk.",
            "Choose door-to-door collection or community bin service per local rules.",
            "Pay user charges if applicable.",
        ],
        "official_website": "https://kerala.gov.in",
        "support_channel": "Municipal health / sanitation department",
    },
    "property_tax": {
        "documents_required": ["Property document", "Previous tax receipt if any", "Identity proof"],
        "steps": [
            "Log in to the local body revenue portal or visit the tax counter.",
            "Verify assessment details and pay online or at the office.",
            "Save the receipt for records.",
        ],
        "official_website": "https://kerala.gov.in",
        "support_channel": "Municipal revenue / tax section",
    },
    "sewage_connection": {
        "documents_required": ["Building plan approval", "Address proof", "NOC as per local rules"],
        "steps": [
            "Apply to municipal engineering / sewerage department.",
            "Submit site plan and connection fee payment.",
            "Coordinate inspection and connection date.",
        ],
        "official_website": "https://kerala.gov.in",
        "support_channel": "Municipal engineering department",
    },
    "generic_civic_service": {
        "documents_required": ["Valid photo ID", "Address proof", "Passport-size photos", "Supporting documents listed on the official portal"],
        "steps": [
            "Open the official department or e-district portal for this service.",
            "Check eligibility and the latest document checklist.",
            "Apply online or at the authorised centre and keep the acknowledgement number.",
            "Follow up only through official channels.",
        ],
        "official_website": "https://www.india.gov.in",
        "support_channel": "Department helpline listed on the official portal",
    },
}

LOCATION_COORDS: Dict[str, Tuple[float, float]] = {
    "thalassery": (11.748, 75.4929),
    "ward 8": (11.754, 75.488),
    "ward 12": (11.746, 75.497),
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
    "current nahi hai": "no current",
    "bijli nahi hai": "no electricity",
    "paani nahi aa raha": "no water",
    "road kharab hai": "damaged road",
    "kooda": "garbage",
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

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

CATEGORY_MAP: Dict[str, Dict[str, Any]] = {
    "electricity": {
        "keywords": ["no current", "power cut", "electricity gone", "voltage problem", "transformer", "power outage"],
        "issue": "Power outage",
        "subcategory": "power_supply",
        "department": "Electricity Department / KSEB",
        "complaint_type": "grievance",
        "essential_service": True,
    },
    "garbage": {
        "keywords": ["garbage", "waste", "trash", "not collected", "waste collection", "trash piling"],
        "issue": "Garbage not collected",
        "subcategory": "waste_collection",
        "department": "Municipality Sanitation Department",
        "complaint_type": "grievance",
        "public_health_risk": True,
    },
    "water": {
        "keywords": ["no water", "water supply", "pipe leakage", "drinking water", "water shortage", "pipeline"],
        "issue": "Water supply issue",
        "subcategory": "water_supply",
        "department": "Water Authority",
        "complaint_type": "grievance",
        "essential_service": True,
    },
    "road": {
        "keywords": ["road repair", "pothole", "road damaged", "bad road", "road issue"],
        "issue": "Road repair request",
        "subcategory": "road_maintenance",
        "department": "Public Works Department",
        "complaint_type": "service_request",
    },
    "drainage": {
        "keywords": ["drainage", "drain blocked", "sewage", "overflow", "drain blockage"],
        "issue": "Drainage or sewage issue",
        "subcategory": "drainage_blockage",
        "department": "Municipal Engineering Department",
        "complaint_type": "grievance",
        "public_health_risk": True,
    },
    "police": {
        "keywords": ["theft", "harassment", "violence", "police complaint", "fraud", "unsafe", "crime"],
        "issue": "Public safety complaint",
        "subcategory": "law_and_order",
        "department": "Police Department",
        "complaint_type": "emergency",
        "essential_service": True,
        "safety_risk": True,
    },
    "revenue": {
        "keywords": ["revenue certificate", "income certificate", "ownership certificate", "legal certificate"],
        "issue": "Revenue certificate request",
        "subcategory": "revenue_certificate",
        "department": "Revenue Department",
        "complaint_type": "certificate_request",
        "certificate_delay": True,
    },
    "health": {
        "keywords": ["medical", "hospital", "health", "clinic", "public health"],
        "issue": "Health service issue",
        "subcategory": "public_health",
        "department": "Health Department",
        "complaint_type": "emergency",
        "essential_service": True,
        "public_health_risk": True,
    },
    "street_lights": {
        "keywords": ["street light", "streetlight", "light not working", "junction light"],
        "issue": "Street light not working",
        "subcategory": "street_lighting",
        "department": "Electrical Maintenance Wing",
        "complaint_type": "service_request",
    },
    "certificate_services": {
        "keywords": ["certificate", "document", "service request", "apply certificate"],
        "issue": "Government certificate request",
        "subcategory": "certificate_service",
        "department": "Citizen Service Center",
        "complaint_type": "certificate_request",
        "certificate_delay": True,
    },
}

SEVERITY_KEYWORDS = {
    "emergency": 5,
    "accident": 5,
    "unsafe": 5,
    "danger": 5,
    "children affected": 5,
    "injury": 5,
    "fire": 5,
    "overflow": 4,
    "severe": 3,
    "urgent": 3,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def detect_language(text: str) -> str:
    lowered = text.lower()
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "Malayalam"
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    if any(phrase in lowered for phrase in HINGLISH_NORMALIZATION):
        return "Hinglish"
    if sum(1 for token in ["nahi", "paani", "sadak", "bijli", "hai"] if token in lowered) >= 2:
        return "Hinglish"
    return "English"


def normalize_hinglish(text: str) -> str:
    normalized = text.lower()
    for source, target in HINGLISH_NORMALIZATION.items():
        normalized = normalized.replace(source, target)
    return normalized


def mock_translate_to_english(text: str, language: str) -> str:
    if language in {"Hindi", "Malayalam"}:
        return f"{text} (translated to English - demo)"
    return text


def _number_from_token(token: str) -> Optional[int]:
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token.lower())


def extract_duration(text: str, ai_duration_text: Optional[str] = None) -> Tuple[str, int, Optional[float], Optional[str]]:
    source = f"{text} {ai_duration_text or ''}".strip().lower()
    match = re.search(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
        r"(day|days|week|weeks|month|months|year|years)\b",
        source,
    )
    if not match:
        return "Not specified", 0, None, None

    value = _number_from_token(match.group(1))
    unit = match.group(2)
    if value is None:
        return "Not specified", 0, None, None

    days = value
    if unit.startswith("week"):
        days = value * 7
    elif unit.startswith("month"):
        days = value * 30
    elif unit.startswith("year"):
        days = value * 365

    return f"{value} {unit}", days, float(value), unit


def extract_location(text: str, ai_location: Optional[str] = None) -> str:
    if ai_location:
        cleaned_ai_location = ai_location.strip()
        if cleaned_ai_location and cleaned_ai_location.lower() not in {"unknown", "ward", "the", "our area", "area"}:
            return cleaned_ai_location.title()

    lowered = text.lower()
    ward_match = re.search(r"\bward\s+\d+\b", lowered)
    if ward_match:
        return ward_match.group(0).title()

    pin_match = re.search(r"\bpincode\s+\d{6}\b", lowered)
    if pin_match:
        return pin_match.group(0).title()

    for city in LOCATION_COORDS:
        if city != "unknown" and city in lowered:
            return city.title()

    for pattern in [r"\bnear\s+([a-z0-9\s-]+?)(?:$| for | since | in | at )", r"\bin\s+([a-z0-9\s-]+?)(?:$| for | since | near )"]:
        match = re.search(pattern, lowered)
        if match and match.group(1).strip():
            candidate = match.group(1).strip()
            if candidate.lower() not in {"the", "ward", "our area", "area"}:
                return candidate.title()
    return "Unknown"


def extract_severity_keywords(text: str, ai_keywords: Optional[List[str]] = None) -> List[str]:
    lowered = text.lower()
    found = [keyword for keyword in SEVERITY_KEYWORDS if keyword in lowered]
    if ai_keywords:
        found.extend(keyword.lower() for keyword in ai_keywords if keyword)
    deduped: List[str] = []
    for keyword in found:
        if keyword not in deduped:
            deduped.append(keyword)
    return deduped


def infer_intent(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ["otp", "lottery", "kyc", "click", "scam", "fraud", "prize"]):
        return "scam"
    if any(k in lowered for k in ["aadhaar", "passport", "pan", "loan", "service", "document"]):
        return "service"
    return "complaint"


def _resolve_mode(text: str) -> str:
    try:
        ai_intent = brain.analyze_intent(text).intent
        if ai_intent == "scam_report":
            return "scam"
        if ai_intent == "service_guidance":
            return "service"
        if ai_intent == "complaint_report":
            return "complaint"
    except Exception:
        pass
    return infer_intent(text)


def _classify_from_rules(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    best_category = "general"
    best_config: Dict[str, Any] = {
        "issue": "General civic issue",
        "subcategory": "general_request",
        "department": "Local Administration",
        "complaint_type": "grievance",
    }
    best_score = 0

    for category, config in CATEGORY_MAP.items():
        score = sum(1 for keyword in config["keywords"] if keyword in lowered)
        if score > best_score:
            best_score = score
            best_category = category
            best_config = config

    return {"category": best_category, **best_config}


def _normalize_complaint_type(raw_type: Optional[str], category: str, text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["emergency", "accident", "unsafe", "injury", "fire"]):
        return "emergency"
    if "certificate" in lowered or category in {"revenue", "certificate_services"}:
        return "certificate_request"
    if any(word in lowered for word in ["need", "request", "apply", "not working", "repair"]):
        return "service_request"
    if raw_type:
        value = raw_type.lower().replace(" ", "_")
        if value in {"service_request", "grievance", "emergency", "certificate_request"}:
            return value
    return CATEGORY_MAP.get(category, {}).get("complaint_type", "grievance")


def _normalize_priority_label(score: int) -> str:
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _priority_score(
    category: str,
    complaint_type: str,
    duration_days: int,
    severity_keywords: List[str],
    similar_count: int,
) -> Tuple[int, str, List[str]]:
    config = CATEGORY_MAP.get(category, {})
    score = 0
    reasons: List[str] = []

    if config.get("essential_service") or category in {"electricity", "water", "police", "revenue", "health"}:
        score += 4
        reasons.append("Essential service or critical authority involved")
    elif category in {"garbage", "drainage", "road", "street_lights"}:
        score += 2
        reasons.append("Civic infrastructure impact")

    if complaint_type == "certificate_request":
        score += 3
        reasons.append("Certificate or legal service dependency")
    if complaint_type == "service_request":
        score += 2
        reasons.append("Actionable department service request")
    if complaint_type == "emergency":
        score += 5
        reasons.append("Emergency or public safety complaint")

    if duration_days >= 2:
        score += 2
        reasons.append("Issue duration is more than 2 days")
    if duration_days >= 7:
        score += 2
        reasons.append("Issue duration is more than 7 days")
    if duration_days >= 30:
        score += 3
        reasons.append("Issue duration is more than 30 days")

    if config.get("public_health_risk"):
        score += 4
        reasons.append("Public health risk detected")
    if category in {"electricity", "water"} and duration_days >= 2:
        score += 2
        reasons.append("Essential utility disruption has lasted multiple days")

    if severity_keywords:
        score += min(5, max(SEVERITY_KEYWORDS.get(keyword, 2) for keyword in severity_keywords))
        reasons.append(f"Severity keywords present: {', '.join(severity_keywords[:3])}")

    if similar_count >= 5:
        score += 5
        reasons.append("Many similar complaints found in the same area")
    elif similar_count >= 2:
        score += 2
        reasons.append("Repeated similar complaints in the same area")

    return score, _normalize_priority_label(score), reasons


def _urgency_from_priority(priority: str, severity_keywords: List[str]) -> str:
    if "emergency" in severity_keywords or "accident" in severity_keywords or priority == "high":
        return "High"
    if priority == "medium":
        return "Medium"
    return "Low"


def _allocation_bucket(record_type: str) -> str:
    if record_type == "complaint":
        return "complaints"
    if record_type in ("request", "service"):
        return "requests"
    return "scam"


def _save_record(
    record_type: str,
    raw_input: Dict[str, Any],
    processed_output: Dict[str, Any],
    record_id: str,
    *,
    domain_id: Optional[str] = None,
    domain_title: Optional[str] = None,
    item_id: Optional[str] = None,
    item_title: Optional[str] = None,
) -> HistoryRecord:
    record = HistoryRecord(
        id=record_id,
        type=record_type,  # type: ignore[arg-type]
        created_at=_utcnow(),
        raw_input=raw_input,
        processed_output=processed_output,
    )
    HISTORY_DB.append(record)
    bucket = _allocation_bucket(record_type)
    try:
        persist_record(
            record_id,
            record_type,
            record.created_at,
            raw_input,
            processed_output,
            allocation_bucket=bucket,
            domain_id=domain_id,
            domain_title=domain_title,
            item_id=item_id,
            item_title=item_title,
        )
    except Exception:
        pass
    return record


def load_persistent_records() -> None:
    """Load SQLite civic records into in-memory HISTORY_DB (server startup)."""
    global HISTORY_DB
    init_records_db()
    rows = fetch_all_records()
    if not rows:
        return
    HISTORY_DB.clear()
    for row in rows:
        HISTORY_DB.append(
            HistoryRecord(
                id=row["id"],
                type=row["type"],  # type: ignore[arg-type]
                created_at=datetime.fromisoformat(row["created_at"]),
                raw_input=json.loads(row["raw_json"]),
                processed_output=json.loads(row["processed_json"]),
            )
        )


def get_history(record_type: Optional[str] = None) -> List[HistoryRecord]:
    if record_type is None:
        return HISTORY_DB
    return [record for record in HISTORY_DB if record.type == record_type]


def get_record_by_id(record_id: str) -> Optional[HistoryRecord]:
    return next((record for record in HISTORY_DB if record.id == record_id), None)


def _cluster_key(category: str, location: str) -> str:
    normalized_category = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
    normalized_location = re.sub(r"[^a-z0-9]+", "_", location.lower()).strip("_")
    return f"{normalized_category}::{normalized_location}"


def _recent_matching_complaints(category: str, location: str, days: int = 7) -> List[HistoryRecord]:
    cutoff = _utcnow() - timedelta(days=days)
    matches: List[HistoryRecord] = []
    for record in HISTORY_DB:
        if record.type != "complaint":
            continue
        if record.created_at < cutoff:
            continue
        if record.processed_output.get("category") == category and record.processed_output.get("location") == location:
            matches.append(record)
    return matches


def get_cluster_summaries() -> List[ClusterSummary]:
    complaint_records = [record for record in HISTORY_DB if record.type == "complaint"]
    grouped: Dict[str, List[HistoryRecord]] = defaultdict(list)
    for record in complaint_records:
        key = _cluster_key(
            str(record.processed_output.get("category", "general")),
            str(record.processed_output.get("location", "Unknown")),
        )
        grouped[key].append(record)

    summaries: List[ClusterSummary] = []
    for index, records in enumerate(grouped.values(), start=1):
        sample = records[0].processed_output
        cluster_size = len(records)
        escalated = any(bool(record.processed_output.get("escalated")) for record in records)
        priority = "high" if any(record.processed_output.get("priority") == "high" for record in records) else (
            "medium" if any(record.processed_output.get("priority") == "medium" for record in records) else "low"
        )
        insight = (
            "Repeated complaints indicate a group issue and authority escalation."
            if cluster_size >= 5
            else "Repeated complaints detected in this area."
            if cluster_size >= 2
            else "Single complaint cluster currently being monitored."
        )
        summaries.append(
            ClusterSummary(
                cluster_id=f"cluster_{index}",
                issue_type=str(sample.get("issue_type", "General civic issue")),
                category=str(sample.get("category", "general")),
                department=str(sample.get("department", "Local Administration")),
                location=str(sample.get("location", "Unknown")),
                cluster_size=cluster_size,
                priority=priority,
                escalated=escalated,
                insight=insight,
            )
        )
    return summaries


def _citizen_message(
    issue_type: str,
    category: str,
    department: str,
    duration_text: str,
    priority: str,
    similar_count: int,
    escalated: bool,
) -> str:
    duration_part = (
        f" Since the issue has lasted for {duration_text}, it has been marked {priority} priority."
        if duration_text != "Not specified"
        else f" It has been marked {priority} priority based on the issue type and impact."
    )
    similar_part = (
        f" We also found {similar_count} similar complaint(s) from the same area."
        if similar_count
        else " No recent similar complaints were found in the same area."
    )
    escalation_part = " The case has been escalated for authority attention." if escalated else ""
    return (
        f"Your complaint has been identified as {issue_type.lower()} under the {category} category and routed to "
        f"{department}.{duration_part}{similar_part}{escalation_part}"
    )


def analyze_complaint(payload: ComplaintRequest) -> ComplaintResponse:
    ai_structured = brain.structure_complaint(payload.text)

    language = detect_language(payload.text) if payload.language == "auto" else payload.language
    if ai_structured.detected_language and ai_structured.detected_language != "Unknown":
        language = ai_structured.detected_language

    normalized = normalize_hinglish(payload.text)
    translated = mock_translate_to_english(normalized, language)

    rule_classification = _classify_from_rules(translated)
    ai_category = (ai_structured.category or "").strip().lower().replace(" ", "_")
    if ai_category in CATEGORY_MAP:
        rule_classification = {"category": ai_category, **CATEGORY_MAP[ai_category]}

    category = str(rule_classification["category"])
    issue_type = str(rule_classification["issue"])
    if ai_structured.main_issue and ai_structured.main_issue.lower() != "unknown":
        issue_type = ai_structured.main_issue
    elif ai_structured.issue_type and ai_structured.issue_type.lower() != "unknown":
        issue_type = ai_structured.issue_type
    subcategory = ai_structured.subcategory or str(rule_classification["subcategory"])
    department = ai_structured.required_department or str(rule_classification["department"])
    location = extract_location(translated, ai_structured.location)
    duration_text, duration_days, duration_value, duration_unit = extract_duration(translated, ai_structured.duration_text)
    severity_keywords = extract_severity_keywords(translated, ai_structured.severity_keywords)
    complaint_type = _normalize_complaint_type(ai_structured.complaint_type, category, translated)

    similar_records = _recent_matching_complaints(category, location)
    similar_count = len(similar_records)
    priority_score, priority, priority_reasons = _priority_score(
        category=category,
        complaint_type=complaint_type,
        duration_days=duration_days,
        severity_keywords=severity_keywords,
        similar_count=similar_count,
    )
    group_issue = similar_count >= 2
    escalated = similar_count >= 4 or priority == "high"
    action = "escalate_to_authority" if escalated else "route_to_department"
    urgency = _urgency_from_priority(priority, severity_keywords)
    risk_score = min(100, 15 + priority_score * 9)

    current_clusters = get_cluster_summaries()
    existing = next(
        (
            cluster
            for cluster in current_clusters
            if cluster.category == category and cluster.location.lower() == location.lower()
        ),
        None,
    )
    cluster_size = (existing.cluster_size + 1) if existing else (similar_count + 1)
    cluster_id = existing.cluster_id if existing else f"cluster_{len(current_clusters) + 1}"

    insight = (
        "Community-level issue detected; similar complaints are rising in the same area."
        if group_issue
        else "Structured as an individual complaint and added for trend monitoring."
    )
    citizen_message = _citizen_message(
        issue_type=issue_type,
        category=category,
        department=department,
        duration_text=duration_text,
        priority=priority,
        similar_count=similar_count,
        escalated=escalated,
    )
    confidence = round(0.62 + min(0.33, priority_score / 20), 2)

    record_id = _new_id("cmp")
    structured_output = {
        "original_text": payload.text,
        "intent": "civic_complaint",
        "main_issue": issue_type,
        "issue_type": issue_type,
        "category": category,
        "subcategory": subcategory,
        "department": department,
        "duration_text": duration_text,
        "duration_value": duration_value,
        "duration_unit": duration_unit,
        "duration_days": duration_days,
        "location": location,
        "complaint_type": complaint_type,
        "severity_keywords": severity_keywords,
        "priority": priority,
        "priority_score": priority_score,
        "priority_reasons": priority_reasons,
        "group_issue": group_issue,
        "similar_complaint_count": similar_count,
        "cluster_id": cluster_id,
        "cluster_size": cluster_size,
        "escalated": escalated,
        "action": action,
        "urgency": urgency,
        "risk_score": risk_score,
        "insight": insight,
        "citizen_message": citizen_message,
        "ai_summary": ai_structured.summary,
    }
    if payload.taxonomy_domain_id:
        structured_output["taxonomy_domain_id"] = payload.taxonomy_domain_id
    if payload.taxonomy_item_id:
        structured_output["taxonomy_item_id"] = payload.taxonomy_item_id
    if payload.taxonomy_domain_title:
        structured_output["taxonomy_domain_title"] = payload.taxonomy_domain_title
    if payload.taxonomy_item_title:
        structured_output["taxonomy_item_title"] = payload.taxonomy_item_title

    dom_id = payload.taxonomy_domain_id or category
    dom_title = payload.taxonomy_domain_title
    item_id = payload.taxonomy_item_id
    item_title = payload.taxonomy_item_title

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
        domain_id=dom_id,
        domain_title=dom_title,
        item_id=item_id,
        item_title=item_title,
    )

    return ComplaintResponse(
        record_id=record.id,
        created_at=record.created_at,
        detected_language=language,
        normalized_text=normalized,
        translated_text=translated,
        issue_type=issue_type,
        urgency=urgency,
        complaint_type=complaint_type,
        category=category,
        subcategory=subcategory,
        department=department,
        duration_text=duration_text,
        duration_days=duration_days,
        location=location,
        cluster_id=cluster_id,
        cluster_size=cluster_size,
        risk_score=risk_score,
        priority=priority,
        priority_score=priority_score,
        group_issue=group_issue,
        similar_complaint_count=similar_count,
        escalated=escalated,
        action=action,
        insight=insight,
        citizen_message=citizen_message,
        confidence=confidence,
        structured_output=structured_output,
    )


def analyze_scam(payload: ScamRequest) -> ScamResponse:
    ai_scam = brain.analyze_scam(payload.text)
    text = payload.text.lower()
    matched = [keyword for keyword in SCAM_KEYWORDS if keyword in text]
    score = sum(SCAM_KEYWORDS[keyword] for keyword in matched)

    if payload.url:
        parsed = urlparse(payload.url)
        if parsed.scheme not in {"https", "http"}:
            score += 10
        if parsed.scheme == "http":
            score += 8
        if any(value in parsed.netloc for value in ["bit.ly", "tinyurl", "free", "win"]):
            score += 10

    probability = min(100, max(5, score))
    if ai_scam.scam_detected:
        probability = max(probability, {"high": 88, "medium": 62, "low": 42}.get(ai_scam.risk_level, 55))
    risk_level = "High" if probability >= 75 else "Medium" if probability >= 45 else "Low"

    reason = (
        f"Suspicious markers detected: {', '.join(matched)}."
        if matched
        else "No strong scam markers detected, but caution is advised."
    )
    if ai_scam.scam_detected:
        reason = f"{ai_scam.recommendation} ({reason})"

    insight = "High-risk phishing pattern detected." if probability >= 75 else "No major phishing trend detected."
    confidence = round(0.5 + min(0.45, probability / 200), 2)

    record_id = _new_id("scm")
    structured_output = {
        "scam_probability": probability,
        "risk_level": risk_level,
        "suspicious_keywords": matched,
        "reason": reason,
        "insight": insight,
        "ai_scam": ai_scam.model_dump(),
    }
    record = _save_record(
        record_type="scam",
        raw_input={"text": payload.text, "url": payload.url},
        processed_output=structured_output,
        record_id=record_id,
        domain_id=None,
        domain_title=None,
        item_id=None,
        item_title=None,
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


def get_service_info(service_name: str, *, fallback: str = "aadhaar") -> ServiceInfoResponse:
    key = service_name.lower()
    if key not in SERVICE_CATALOG:
        key = fallback
    template = SERVICE_CATALOG[key]
    readiness = f"You can start the {key.upper()} process after collecting {len(template['documents_required'])} core documents."
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
    taxonomy_item_title: Optional[str] = payload.taxonomy_item_title
    taxonomy_domain_title: Optional[str] = payload.taxonomy_domain_title

    if payload.taxonomy_item_id:
        cat_key = payload.taxonomy_item_id if payload.taxonomy_item_id in SERVICE_CATALOG else "generic_civic_service"
        detail = None
        if payload.taxonomy_domain_id:
            detail = get_item_detail(payload.taxonomy_domain_id, payload.taxonomy_item_id)
        if detail:
            _, it, _ = detail
            taxonomy_item_title = taxonomy_item_title or it.get("title")
            dom, _, _ = detail
            taxonomy_domain_title = taxonomy_domain_title or dom.get("title")
        category = cat_key
    elif category == "auto":
        category = _detect_service_from_text(payload.text)

    fb = "generic_civic_service" if payload.taxonomy_item_id else "aadhaar"
    info = get_service_info(category, fallback=fb)
    output = info.model_dump()
    output["service_name"] = taxonomy_item_title or output.get("service_name", category)
    if category == "generic_civic_service" and taxonomy_item_title:
        output["readiness_summary"] = (
            f"You can start the {taxonomy_item_title} process after collecting the listed documents and checking the official portal."
        )
    output["detected_language"] = language
    output["normalized_text"] = normalized
    output["intent"] = "request" if payload.taxonomy_item_id else "service"
    if payload.taxonomy_domain_id:
        output["taxonomy_domain_id"] = payload.taxonomy_domain_id
    if payload.taxonomy_item_id:
        output["taxonomy_item_id"] = payload.taxonomy_item_id
    if taxonomy_domain_title:
        output["taxonomy_domain_title"] = taxonomy_domain_title
    if taxonomy_item_title:
        output["taxonomy_item_title"] = taxonomy_item_title

    save_type = "request" if payload.taxonomy_item_id else "service"
    record_id = _new_id("req" if save_type == "request" else "svc")
    record = _save_record(
        save_type,
        raw_input={
            "text": payload.text,
            "language": payload.language,
            "service_category": payload.service_category,
            "taxonomy_domain_id": payload.taxonomy_domain_id,
            "taxonomy_item_id": payload.taxonomy_item_id,
        },
        processed_output=output,
        record_id=record_id,
        domain_id=payload.taxonomy_domain_id,
        domain_title=taxonomy_domain_title,
        item_id=payload.taxonomy_item_id,
        item_title=taxonomy_item_title,
    )
    output["record_id"] = record.id
    output["created_at"] = record.created_at.isoformat()
    return output


def route_input(text: str, language: str = "auto", mode: str = "auto") -> Dict[str, Any]:
    selected_mode = _resolve_mode(text) if mode == "auto" else mode.lower()
    if selected_mode == "scam":
        result = analyze_scam(ScamRequest(text=text))
        return {"mode": "scam", "response": result.model_dump()}
    if selected_mode == "service":
        result = service_guidance(ServiceGuidanceRequest(text=text, language=language, service_category="auto"))
        return {"mode": "service", "response": result}
    result = analyze_complaint(ComplaintRequest(text=text, language=language, complaint_mode="general"))
    return {"mode": "complaint", "response": result.model_dump()}


def get_dashboard_data() -> DashboardResponse:
    complaint_records = [record for record in HISTORY_DB if record.type == "complaint"]
    scam_records = [record for record in HISTORY_DB if record.type == "scam"]
    service_records = [record for record in HISTORY_DB if record.type == "service"]
    request_records = [record for record in HISTORY_DB if record.type in ("request", "service")]

    issue_counter = Counter(str(record.processed_output.get("issue_type", "General civic issue")) for record in complaint_records)
    location_counter = Counter(str(record.processed_output.get("location", "Unknown")) for record in complaint_records)
    priority_counter = Counter(str(record.processed_output.get("priority", "low")).title() for record in complaint_records)
    department_counter = Counter(str(record.processed_output.get("department", "Local Administration")) for record in complaint_records)
    complaint_type_counter = Counter(
        str(record.processed_output.get("complaint_type", "grievance")).replace("_", " ").title()
        for record in complaint_records
    )
    urgency_counter = Counter(str(record.processed_output.get("urgency", "Low")) for record in complaint_records)

    timeline_counter = Counter(record.created_at.date().isoformat() for record in complaint_records)
    priority_timeline: Dict[str, Counter[str]] = defaultdict(Counter)
    for record in complaint_records:
        day = record.created_at.date().isoformat()
        priority_timeline[day][str(record.processed_output.get("priority", "low")).title()] += 1

    timeline = [{"date": day, "count": count} for day, count in sorted(timeline_counter.items())]
    stacked_timeline = [
        {
            "date": day,
            "High": counts.get("High", 0),
            "Medium": counts.get("Medium", 0),
            "Low": counts.get("Low", 0),
        }
        for day, counts in sorted(priority_timeline.items())
    ]

    cluster_alerts = [
        {
            "cluster_id": cluster.cluster_id,
            "location": cluster.location,
            "category": cluster.category,
            "count": cluster.cluster_size,
            "priority": cluster.priority.title(),
            "escalated": cluster.escalated,
        }
        for cluster in sorted(get_cluster_summaries(), key=lambda item: item.cluster_size, reverse=True)[:6]
    ]

    return DashboardResponse(
        total_complaints=len(complaint_records),
        most_common_issue=issue_counter.most_common(1)[0][0] if issue_counter else "N/A",
        high_urgency_count=urgency_counter.get("High", 0),
        complaints_by_type=dict(issue_counter),
        complaints_by_location=dict(location_counter),
        complaints_by_priority=dict(priority_counter),
        complaints_by_department=dict(department_counter),
        complaints_by_complaint_type=dict(complaint_type_counter),
        timeline=timeline,
        priority_timeline=stacked_timeline,
        cluster_alerts=cluster_alerts,
        top_area=location_counter.most_common(1)[0][0] if location_counter else "N/A",
        total_scam_checks=len(scam_records),
        total_service_queries=len(service_records),
        total_requests=len(request_records),
        total_clusters=len(get_cluster_summaries()),
    )


def get_allocation_tree() -> Dict[str, Any]:
    """Folder-style grouping: complaints vs requests → department → records."""
    complaints: Dict[str, List[Dict[str, Any]]] = {}
    requests: Dict[str, List[Dict[str, Any]]] = {}

    def _status_meta(record: HistoryRecord) -> Tuple[str, str]:
        po = record.processed_output
        txt = f"{record.raw_input.get('text', '')} {po.get('status', '')}".lower()
        if any(x in txt for x in ("completed", "resolved", "fixed", "done", "closed")):
            return "completed", "check-circle"
        if record.type == "scam":
            return "completed", "check-circle"
        if po.get("escalated") or "escalate" in str(po.get("action", "")):
            return "in_progress", "loader"
        if po.get("priority") == "high":
            return "in_progress", "loader"
        return "pending", "clock"

    def _request_department(po: Dict[str, Any]) -> str:
        explicit = str(po.get("department") or "").strip()
        if explicit:
            return explicit
        item = str(po.get("taxonomy_item_title") or po.get("service_name") or "").lower()
        if any(k in item for k in ("electric", "kseb", "power")):
            return "Electricity Department / KSEB"
        if any(k in item for k in ("water", "sewage", "drain")):
            return "Water Authority / Municipal Engineering"
        if any(k in item for k in ("passport",)):
            return "Passport Seva"
        if any(k in item for k in ("aadhaar",)):
            return "UIDAI Services"
        if any(k in item for k in ("pan",)):
            return "Income Tax / PAN Services"
        if any(k in item for k in ("driving", "licence", "license", "dl")):
            return "Motor Vehicles Department"
        if any(k in item for k in ("health", "hospital")):
            return "Health Department"
        return "Citizen Service Center"

    for record in HISTORY_DB:
        po = record.processed_output
        if record.type == "complaint":
            dept = str(po.get("department") or "Local Administration")
            status, icon = _status_meta(record)
            complaints.setdefault(dept, []).append(
                {
                    "id": record.id,
                    "type": record.type,
                    "created_at": record.created_at.isoformat(),
                    "department": dept,
                    "domain_title": str(po.get("taxonomy_domain_title") or po.get("category") or "general"),
                    "item_title": po.get("taxonomy_item_title") or po.get("issue_type"),
                    "summary": po.get("citizen_message") or po.get("issue_type") or "",
                    "location": po.get("location"),
                    "priority": po.get("priority"),
                    "status": status,
                    "status_icon": icon,
                }
            )
        elif record.type in ("request", "service"):
            dept = _request_department(po)
            status, icon = _status_meta(record)
            requests.setdefault(dept, []).append(
                {
                    "id": record.id,
                    "type": record.type,
                    "created_at": record.created_at.isoformat(),
                    "department": dept,
                    "domain_title": str(po.get("taxonomy_domain_title") or "Service requests"),
                    "item_title": po.get("taxonomy_item_title") or po.get("service_name"),
                    "summary": po.get("readiness_summary") or "",
                    "status": status,
                    "status_icon": icon,
                }
            )

    return {"complaints": complaints, "requests": requests}


def get_map_data() -> List[MapPoint]:
    points: List[MapPoint] = []
    for record in HISTORY_DB:
        if record.type != "complaint":
            continue
        location = str(record.processed_output.get("location", "Unknown"))
        lat, lon = LOCATION_COORDS.get(location.lower(), LOCATION_COORDS["unknown"])
        points.append(
            MapPoint(
                lat=lat,
                lon=lon,
                issue=str(record.processed_output.get("issue_type", "General civic issue")),
                location=location,
                urgency=str(record.processed_output.get("priority", "low")).title(),
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
        "Received raw user input from the frontend.",
        "Applied language detection and text normalization rules.",
        "Ran hybrid extraction using LLM hints plus rule-based classification.",
        "Scored priority using explainable complaint, duration, severity, and clustering rules.",
        "Saved the structured record in demo in-memory storage.",
    ]
    reasoning_summary = (
        "The complaint pipeline combines LLM-assisted extraction with deterministic category mapping, priority scoring, and area clustering."
    )
    confidence_summary = (
        "Confidence reflects rule coverage, structured field availability, and consistency across category, duration, and priority signals."
    )

    markdown_report = "\n".join(
        [
            "# CivicSafe AI Processing Report",
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
