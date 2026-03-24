from typing import Any
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    raw_text: str = Field(min_length=1)


class IntentAnalysis(BaseModel):
    intent: str
    confidence: float


class StructuredComplaint(BaseModel):
    issue_type: str = "Unknown"
    location: str | None = None
    urgency: str = "Medium"
    summary: str = "Unable to parse complaint"
    category: str = "Other"
    detected_language: str = "Unknown"
    required_department: str | None = None
    priority_tag: str | None = None
    suggested_next_step: str | None = None
    cluster_key: str | None = None


class ScamAnalysis(BaseModel):
    scam_detected: bool = False
    scam_type: str = "none"
    risk_level: str = "low"
    recommendation: str = "No scam indicators found."


class ClusterInfo(BaseModel):
    cluster_key: str | None = None
    cluster_ready: bool = False


class ConfidenceInfo(BaseModel):
    overall_confidence: float
    intent_confidence: float
    structure_confidence: float
    scam_confidence: float


class AnalyzeResponse(BaseModel):
    intent: IntentAnalysis
    structured_data: StructuredComplaint
    scam_analysis: ScamAnalysis
    cluster_info: ClusterInfo
    confidence: ConfidenceInfo
    report_available: bool = True


class ReportRequest(BaseModel):
    raw_text: str
    analysis: AnalyzeResponse


class ReportResponse(BaseModel):
    json_report: dict[str, Any]
    markdown_report: str


class TranscribeResponse(BaseModel):
    text: str
