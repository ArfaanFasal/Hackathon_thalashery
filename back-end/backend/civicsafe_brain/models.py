from pydantic import BaseModel


class IntentAnalysis(BaseModel):
    intent: str
    confidence: float


class StructuredComplaint(BaseModel):
    issue_type: str = "Unknown"
    main_issue: str | None = None
    complaint_type: str | None = None
    subcategory: str | None = None
    location: str | None = None
    urgency: str = "Medium"
    summary: str = "Unable to parse complaint"
    category: str = "Other"
    detected_language: str = "Unknown"
    required_department: str | None = None
    duration_text: str | None = None
    duration_value: float | None = None
    duration_unit: str | None = None
    severity_keywords: list[str] = []
    priority_tag: str | None = None
    suggested_next_step: str | None = None
    cluster_key: str | None = None


class ScamAnalysis(BaseModel):
    scam_detected: bool = False
    scam_type: str = "none"
    risk_level: str = "low"
    recommendation: str = "No scam indicators found."
