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
    location: str
    cluster_id: str
    cluster_size: int
    risk_score: int
    insight: str
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
    """Mock output for voice-to-text conversion."""

    converted_text: str
    language: str


class DashboardResponse(BaseModel):
    """Aggregated data for dashboard and charts."""

    total_complaints: int
    most_common_issue: str
    high_urgency_count: int
    complaints_by_type: Dict[str, int]
    complaints_by_location: Dict[str, int]
    timeline: List[Dict[str, Any]]
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
    location: str
    cluster_size: int
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
