"""Pydantic request/response models for CivicSafe AI backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


RecordType = Literal["complaint", "scam", "service"]


class RouteInputRequest(BaseModel):
    """Unified route-input request from chat-style frontend."""

    text: str = Field(..., min_length=1)
    language: str = "auto"
    mode: str = "auto"


class ComplaintRequest(BaseModel):
    """Complaint analysis request payload."""

    text: str = Field(..., min_length=1)
    language: str = "auto"
    complaint_mode: str = "general"


class ComplaintResponse(BaseModel):
    """Structured complaint analysis response."""

    record_id: str
    record_type: RecordType = "complaint"
    created_at: datetime
    detected_language: str
    normalized_text: str
    translated_text: str
    issue_type: str
    urgency: str
    complaint_type: str
    category: str
    subcategory: str
    department: str
    duration_text: str
    duration_days: int
    location: str
    cluster_id: str
    cluster_size: int
    risk_score: int
    priority: str
    priority_score: int
    group_issue: bool
    similar_complaint_count: int
    escalated: bool
    action: str
    insight: str
    citizen_message: str
    confidence: float
    structured_output: Dict[str, Any]


class ScamRequest(BaseModel):
    """Scam analysis request payload."""

    text: str = Field(..., min_length=1)
    url: Optional[str] = None


class ScamResponse(BaseModel):
    """Scam check response."""

    record_id: str
    record_type: RecordType = "scam"
    created_at: datetime
    scam_probability: int
    risk_level: str
    suspicious_keywords: List[str]
    reason: str
    insight: str
    confidence: float
    structured_output: Dict[str, Any]


class ServiceGuidanceRequest(BaseModel):
    """Service guidance request payload."""

    text: str = Field(..., min_length=1)
    language: str = "auto"
    service_category: str = "auto"


class ServiceInfoResponse(BaseModel):
    """Standardized service information response."""

    service_name: str
    documents_required: List[str]
    steps: List[str]
    official_website: str
    support_channel: str
    readiness_summary: str


class VoiceResponse(BaseModel):
    """Voice-to-text conversion output."""

    converted_text: str
    language: str
    mode: str
    provider: str
    detail: str


class DashboardResponse(BaseModel):
    """Aggregated data for dashboard and charts."""

    total_complaints: int
    most_common_issue: str
    high_urgency_count: int
    complaints_by_type: Dict[str, int]
    complaints_by_location: Dict[str, int]
    complaints_by_priority: Dict[str, int]
    complaints_by_department: Dict[str, int]
    complaints_by_complaint_type: Dict[str, int]
    timeline: List[Dict[str, Any]]
    priority_timeline: List[Dict[str, Any]]
    cluster_alerts: List[Dict[str, Any]]
    top_area: str
    total_scam_checks: int
    total_service_queries: int
    total_clusters: int


class MapPoint(BaseModel):
    """Map point generated from complaint location info."""

    lat: float
    lon: float
    issue: str
    location: str
    urgency: str


class ClusterSummary(BaseModel):
    """Complaint cluster summary."""

    cluster_id: str
    issue_type: str
    category: str
    department: str
    location: str
    cluster_size: int
    priority: str
    escalated: bool
    insight: str


class ReportRequest(BaseModel):
    """Report generation request."""

    record_type: RecordType
    record_id: str


class ReportResponse(BaseModel):
    """Explainable processing report response."""

    record_id: str
    record_type: RecordType
    raw_input: Dict[str, Any]
    detected_language: str
    normalized_text: str
    intent: str
    structured_output: Dict[str, Any]
    processing_steps: List[str]
    reasoning_summary: str
    confidence_summary: str
    markdown_report: str


class HistoryRecord(BaseModel):
    """Persistent history record shape."""

    id: str
    type: RecordType
    created_at: datetime
    raw_input: Dict[str, Any]
    processed_output: Dict[str, Any]


# --- Chat-first API (user-facing: no raw JSON in UI) ---


class QuickReply(BaseModel):
    id: str
    label: str


class SummaryCardField(BaseModel):
    label: str
    value: str


class SummaryCard(BaseModel):
    title: str
    subtitle: Optional[str] = None
    fields: List[SummaryCardField] = Field(default_factory=list)
    badges: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class ScamBanner(BaseModel):
    show: bool = False
    risk_level: str = "Low"
    headline: str = ""
    advice: str = ""
    escalation: str = ""


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(default="", max_length=8000)
    quick_reply_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    quick_replies: List[QuickReply] = Field(default_factory=list)
    summary_card: Optional[SummaryCard] = None
    scam_banner: Optional[ScamBanner] = None
    case_complete: bool = False
    stage: str = "A"
