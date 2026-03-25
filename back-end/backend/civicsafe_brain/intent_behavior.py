"""
Civic chat intent identification + grouped-complaint escalation signals.

Hybrid: OpenAI JSON classification + lightweight rules + rolling similarity counts.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

from civicsafe_brain import escalation_store as esc
from civicsafe_brain.config import settings

DetectedIntent = Literal[
    "complaint",
    "request",
    "query",
    "follow_up",
    "emergency",
    "general_conversation",
]


class FrontendStatusPayload(BaseModel):
    """UI-ready card (timeline + badges)."""

    title: str = ""
    subtitle: Optional[str] = None
    chat_type: str = ""
    priority_badge: str = "Medium"
    allocation_status: str = ""
    authority_status: str = "Not Sent"
    group_warning: Optional[str] = None
    escalation_status: str = "Normal"
    timeline: list[str] = Field(default_factory=list)


class IntentBehaviorResult(BaseModel):
    original_text: str
    detected_intent: DetectedIntent
    intent_confidence: float = 0.0
    complaint_or_request_flag: Literal["complaint", "request", "neither"] = "neither"

    @field_validator("complaint_or_request_flag", mode="before")
    @classmethod
    def _coerce_flag(cls, v: Any) -> str:
        s = str(v or "neither").lower()
        if s in ("complaint", "request", "neither"):
            return s
        return "neither"
    urgency_type: str = "normal"
    action_required: bool = False
    region_detected: Optional[str] = None
    issue_category: str = "general_public"
    similar_case_count: int = 0
    grouped_issue: bool = False
    escalation_required: bool = False
    priority: Literal["low", "medium", "high"] = "medium"
    department_allocation_status: str = "pending_allocation"
    authority_notification_status: str = "not_sent"
    assigned_department_hint: Optional[str] = None
    user_facing_message: str = ""
    dashboard_status_label: str = ""
    frontend_status: FrontendStatusPayload = Field(default_factory=FrontendStatusPayload)

    def model_dump_public(self) -> dict[str, Any]:
        return self.model_dump()


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


_GREETING_RE = re.compile(
    r"^(hi|hello|hey|hii|namaste|good morning|good evening|good afternoon)\b",
    re.I,
)
_UNCERTAIN_RE = re.compile(
    r"^(i\s+don'?t\s+know|i\s+dunno|no\s+idea|not\s+sure)\b",
    re.I,
)


def _heuristic_general(text: str) -> Optional[IntentBehaviorResult]:
    t = text.strip()
    low = t.lower()
    if low in {"request", "requests", "service", "services", "apply", "application"}:
        fs = FrontendStatusPayload(
            title="Request intent identified",
            subtitle="Application / service path",
            chat_type="Request",
            priority_badge="Medium",
            allocation_status="Pending allocation",
            authority_status="Not Sent",
            escalation_status="Normal",
            timeline=["Chat Received", "Intent Identified", "Request Registered"],
        )
        return IntentBehaviorResult(
            original_text=t,
            detected_intent="request",
            intent_confidence=0.9,
            complaint_or_request_flag="request",
            urgency_type="service_request",
            action_required=True,
            region_detected=None,
            issue_category="service_request",
            similar_case_count=0,
            grouped_issue=False,
            escalation_required=False,
            priority="medium",
            department_allocation_status="pending_allocation",
            authority_notification_status="not_sent",
            user_facing_message="Got it. This is a request flow. Tell me what service you want (for example Aadhaar update, water connection, electricity connection).",
            dashboard_status_label="Request Registered",
            frontend_status=fs,
        )
    if len(low) <= 32 and _GREETING_RE.match(low):
        return _result_general(
            t,
            "Hello — I'm here for civic services, complaints, applications, or safety questions. "
            "What would you like help with today?",
            "Chat Received",
        )
    if len(low) <= 24 and low in {"ok", "okay", "thanks", "thank you", "thx", "bye"}:
        return _result_general(
            t,
            "You're welcome. If something civic comes up—water, roads, documents, or safety—just tell me.",
            "Chat Received",
        )
    if len(low) <= 48 and _UNCERTAIN_RE.match(low):
        return _result_general(
            t,
            "No problem. In your own words, is something not working in your area (like water or garbage), "
            "or are you trying to apply for a certificate or service?",
            "Intent Identified",
        )
    return None


def _result_general(text: str, msg: str, dash: str) -> IntentBehaviorResult:
    fs = FrontendStatusPayload(
        title="Civic assistant",
        subtitle="Tell us what you need",
        chat_type="General",
        priority_badge="—",
        allocation_status="Not applicable",
        authority_status="Not Sent",
        escalation_status="Normal",
        timeline=["Chat Received", "Intent Identified"],
    )
    return IntentBehaviorResult(
        original_text=text,
        detected_intent="general_conversation",
        intent_confidence=0.92,
        complaint_or_request_flag="neither",
        urgency_type="none",
        action_required=False,
        region_detected=None,
        issue_category="general_public",
        similar_case_count=0,
        grouped_issue=False,
        escalation_required=False,
        priority="low",
        department_allocation_status="not_applicable",
        authority_notification_status="not_sent",
        user_facing_message=msg,
        dashboard_status_label=dash,
        frontend_status=fs,
    )


def _map_department(issue: str) -> str:
    low = issue.lower()
    if any(k in low for k in ("garbage", "sanitation", "waste", "sewage")):
        return "Sanitation Department"
    if any(k in low for k in ("electric", "power", "current", "wire")):
        return "Electricity Board"
    if any(k in low for k in ("water", "supply", "pipe")):
        return "Water Authority"
    if any(k in low for k in ("drain", "flood", "overflow")):
        return "Drainage / Public Works"
    if any(k in low for k in ("road", "pothole", "street light", "streetlight")):
        return "Public Works Department"
    if any(k in low for k in ("revenue", "certificate", "income certificate", "permit")):
        return "Revenue Department"
    return "Municipal / Concerned Department"


def _escalation_from_counts(issue_category: str, c7: int, c2: int) -> tuple[bool, str, str]:
    """(grouped_issue, urgency_type, priority)."""
    ic = issue_category.lower()
    if any(x in ic for x in ("garbage", "sanitation", "waste")) and c7 >= 5:
        return True, "community_escalation", "high"
    if any(x in ic for x in ("electric", "power", "current")) and c2 >= 4:
        return True, "community_escalation", "high"
    if any(x in ic for x in ("drain", "sewage", "sewer", "overflow")) and c7 >= 3:
        return True, "community_escalation", "high"
    if any(x in ic for x in ("health", "mosquito", "dengue")) and c7 >= 3:
        return True, "community_escalation", "high"
    return False, "normal", "medium"


def _fill_frontend_timeline(ib: IntentBehaviorResult) -> None:
    steps = ["Chat Received", "Intent Identified"]
    intent = ib.detected_intent
    if intent in ("complaint", "emergency"):
        steps.append("Complaint Registered" if intent == "complaint" else "Emergency Flagged")
    elif intent == "request":
        steps.append("Request Registered")
    elif intent == "query":
        steps.append("Query Classified")
    elif intent == "follow_up":
        steps.append("Follow-up Noted")

    if ib.region_detected:
        steps.append("Region Matched")
    steps.append("Similar Cases Checked")
    if ib.priority == "high":
        steps.append("High Priority Marked")
    if ib.department_allocation_status.startswith("allocated"):
        steps.append("Allocated to Responsible Department")
    if ib.authority_notification_status.startswith("sent"):
        steps.append("Sent to Responsible Authority")

    ib.frontend_status.timeline = steps
    ib.frontend_status.title = ib.dashboard_status_label or "Civic status"
    ib.frontend_status.subtitle = ib.region_detected or ib.issue_category
    ib.frontend_status.chat_type = intent.replace("_", " ").title()
    ib.frontend_status.priority_badge = ib.priority.title()
    ib.frontend_status.allocation_status = ib.department_allocation_status.replace("_", " ").title()
    ib.frontend_status.authority_status = ib.authority_notification_status.replace("_", " ").title()
    ib.frontend_status.escalation_status = "Escalated" if ib.escalation_required else "Normal"
    if ib.grouped_issue:
        ib.frontend_status.group_warning = "Multiple similar complaints found in this area"


def _llm_classify(text: str) -> dict[str, Any] | None:
    client = _client()
    if not client:
        return None
    schema_hint = (
        '{"detected_intent":"complaint|request|query|follow_up|emergency|general_conversation",'
        '"intent_confidence":0.0-1.0,'
        '"complaint_or_request_flag":"complaint|request|neither",'
        '"urgency_type":"normal|service_request|emergency|community_escalation|informational|status_inquiry|none",'
        '"action_required":true|false,'
        '"region_detected":string_or_null,'
        '"issue_category":"short snake_case label e.g. sanitation_electricity_water",'
        '"assigned_department_hint":string_or_null,'
        '"user_facing_message":"one short helpful sentence for the citizen",'
        '"dashboard_status_label":"short label"}'
    )
    prompt = (
        "You classify civic helpdesk chat for India. Understand short, informal, or mixed English.\n"
        "Intents:\n"
        "- complaint: reporting a civic fault, delay, or public inconvenience.\n"
        "- request: wants a government service, document, permit, or processing.\n"
        "- query: how-to, eligibility, timings, documents list, where is office (not applying now).\n"
        "- follow_up: status on existing complaint/request/application.\n"
        "- emergency: immediate danger or safety risk (fire risk, live wire, flooding homes, tree blocking road).\n"
        "- general_conversation: hi/hello/thanks/unclear with no civic content.\n"
        "Rules: Do NOT label a greeting as complaint. Do NOT label a status question as a new complaint. "
        "If the user wants a NEW utility connection or application (water/electricity meter, KSEB connection), "
        "use intent request, not complaint. If supply is OUT or broken (no water, power cut, leak), use complaint. "
        "Extract region if user mentions ward/area/locality/village/taluk. "
        f"Return strict JSON only with keys: {schema_hint}\nText:\n{text}"
    )
    try:
        res = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You reply with strict JSON only, no markdown."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.05,
            max_tokens=550,
        )
        raw = (res.choices[0].message.content or "").strip()
        return json.loads(raw or "{}")
    except Exception:
        return None


def _fallback_classify(text: str) -> dict[str, Any]:
    low = text.lower()
    if any(k in low for k in ("wire", "fire", "flooding", "fell on road", "electrocution", "danger")):
        return {
            "detected_intent": "emergency",
            "intent_confidence": 0.75,
            "complaint_or_request_flag": "complaint",
            "urgency_type": "emergency",
            "action_required": True,
            "region_detected": None,
            "issue_category": "safety_emergency",
            "assigned_department_hint": "Disaster / Emergency response",
            "user_facing_message": "This sounds urgent. I've flagged it as a safety-related report.",
            "dashboard_status_label": "Emergency Flagged",
        }
    if any(
        k in low
        for k in (
            "status",
            "update",
            "what happened",
            "approved",
            "any news",
            "ticket",
            "complaint id",
            "reference",
        )
    ):
        return {
            "detected_intent": "follow_up",
            "intent_confidence": 0.7,
            "complaint_or_request_flag": "neither",
            "urgency_type": "status_inquiry",
            "action_required": True,
            "region_detected": None,
            "issue_category": "follow_up",
            "assigned_department_hint": None,
            "user_facing_message": "For status, use your acknowledgement number on the department portal or helpline.",
            "dashboard_status_label": "Follow-up",
        }
    if any(k in low for k in ("how to", "where is", "what documents", "timing", "eligibility")):
        return {
            "detected_intent": "query",
            "intent_confidence": 0.68,
            "complaint_or_request_flag": "neither",
            "urgency_type": "informational",
            "action_required": False,
            "region_detected": None,
            "issue_category": "information",
            "assigned_department_hint": None,
            "user_facing_message": "I can walk you through the steps—tell me which scheme or document you mean.",
            "dashboard_status_label": "Query",
        }
    if any(
        k in low
        for k in (
            "new water connection",
            "water connection",
            "electricity connection",
            "new electricity",
            "apply for water",
            "apply for electricity",
            "kseb connection",
            "new meter",
            "connection application",
        )
    ) and not any(
        s in low
        for s in ("no water", "water shortage", "power cut", "no electricity", "leak", "outage", "not coming")
    ):
        return {
            "detected_intent": "request",
            "intent_confidence": 0.78,
            "complaint_or_request_flag": "request",
            "urgency_type": "service_request",
            "action_required": True,
            "region_detected": None,
            "issue_category": "utility_connection_request",
            "assigned_department_hint": _map_department("water" if "water" in low else "electric"),
            "user_facing_message": "I've noted this as a connection or application request—not an outage report.",
            "dashboard_status_label": "Request Registered",
        }
    if any(k in low for k in ("need certificate", "apply for", "want to apply", "permit", "license")):
        return {
            "detected_intent": "request",
            "intent_confidence": 0.7,
            "complaint_or_request_flag": "request",
            "urgency_type": "service_request",
            "action_required": True,
            "region_detected": None,
            "issue_category": "service_request",
            "assigned_department_hint": _map_department("certificate"),
            "user_facing_message": "I've noted this as a service request and can outline documents and steps next.",
            "dashboard_status_label": "Request Registered",
        }
    return {
        "detected_intent": "complaint",
        "intent_confidence": 0.62,
        "complaint_or_request_flag": "complaint",
        "urgency_type": "normal",
        "action_required": True,
        "region_detected": None,
        "issue_category": "general_public",
        "assigned_department_hint": _map_department("general"),
        "user_facing_message": "I've logged this as a civic complaint signal—tell me the location and what is affected.",
        "dashboard_status_label": "Complaint Identified",
    }


def analyze_intent_behavior(text: str, *, record_complaint_signal: bool = True) -> IntentBehaviorResult:
    """
    Main entry: classify message + optional grouped escalation counts for complaints/emergencies.
    When record_complaint_signal is True and intent is complaint/emergency, append to rolling store.
    """
    raw = (text or "").strip()
    if not raw:
        return IntentBehaviorResult(
            original_text="",
            detected_intent="general_conversation",
            intent_confidence=0.5,
            user_facing_message="Please type a short message so I can help.",
            dashboard_status_label="Chat Received",
        )

    h = _heuristic_general(raw)
    if h:
        return h

    data = _llm_classify(raw) or _fallback_classify(raw)
    intent = str(data.get("detected_intent", "complaint")).lower()
    if intent not in (
        "complaint",
        "request",
        "query",
        "follow_up",
        "emergency",
        "general_conversation",
    ):
        intent = "complaint"

    region = data.get("region_detected")
    if region is not None:
        region = str(region).strip() or None
    issue_cat = str(data.get("issue_category") or "general_public")

    ib = IntentBehaviorResult(
        original_text=raw,
        detected_intent=intent,  # type: ignore[arg-type]
        intent_confidence=float(data.get("intent_confidence") or 0.75),
        complaint_or_request_flag=data.get("complaint_or_request_flag") or "neither",
        urgency_type=str(data.get("urgency_type") or "normal"),
        action_required=bool(data.get("action_required", True)),
        region_detected=region,
        issue_category=issue_cat,
        user_facing_message=str(data.get("user_facing_message") or "").strip()
        or "Your message has been classified for the helpdesk.",
        dashboard_status_label=str(data.get("dashboard_status_label") or "Intent Identified"),
        assigned_department_hint=data.get("assigned_department_hint"),
    )

    dept = ib.assigned_department_hint or _map_department(issue_cat)

    # Escalation path only for complaint-like traffic
    if intent in ("complaint", "emergency"):
        if record_complaint_signal:
            esc.record_signal(region, issue_cat)
        c7 = esc.count_similar(region, issue_cat, days=7)
        c2 = esc.count_similar(region, issue_cat, days=2)
        ib.similar_case_count = c7
        grouped, urg, pri = _escalation_from_counts(issue_cat, c7, c2)
        ib.grouped_issue = grouped
        if grouped:
            ib.escalation_required = True
            ib.urgency_type = urg
            ib.priority = pri  # type: ignore[assignment]
            ib.department_allocation_status = f"allocated_to_{dept.lower().replace(' ', '_')}"
            ib.authority_notification_status = "sent_to_responsible_authority"
            ib.user_facing_message = (
                "Multiple similar complaints have been detected in your area. "
                "This issue has been marked high priority and forwarded to the responsible authority."
            )
            ib.dashboard_status_label = "Escalated to Department"
        else:
            ib.priority = "high" if intent == "emergency" else "medium"  # type: ignore[assignment]
            ib.escalation_required = intent == "emergency"
            ib.department_allocation_status = (
                "pending_allocation" if not region else f"allocated_to_{dept.lower().replace(' ', '_')}"
            )
            ib.authority_notification_status = "not_sent"
        ib.frontend_status = FrontendStatusPayload(
            title=ib.dashboard_status_label,
            subtitle=region or issue_cat,
            chat_type="Complaint" if intent == "complaint" else "Emergency",
            priority_badge=ib.priority.title(),
            allocation_status=ib.department_allocation_status.replace("_", " ").title(),
            authority_status=ib.authority_notification_status.replace("_", " ").title(),
        )
    elif intent == "request":
        ib.complaint_or_request_flag = "request"
        ib.department_allocation_status = f"allocated_to_{dept.lower().replace(' ', '_')}"
        ib.priority = "medium"  # type: ignore[assignment]
        ib.frontend_status = FrontendStatusPayload(
            title="Request Allocated",
            subtitle=dept,
            chat_type="Request",
            priority_badge="Medium",
            allocation_status=ib.department_allocation_status.replace("_", " ").title(),
            authority_status="Not Sent",
        )
    elif intent == "query":
        ib.complaint_or_request_flag = "neither"
        ib.department_allocation_status = "information_only"
        ib.priority = "low"  # type: ignore[assignment]
        ib.frontend_status = FrontendStatusPayload(
            title="Query Classified",
            subtitle="Information",
            chat_type="Query",
            priority_badge="Low",
            allocation_status="Not applicable",
            authority_status="Not Sent",
        )
    elif intent == "follow_up":
        ib.complaint_or_request_flag = "neither"
        ib.department_allocation_status = "existing_case_lookup"
        ib.frontend_status = FrontendStatusPayload(
            title="Follow-up",
            subtitle="Status check",
            chat_type="Follow-up",
            priority_badge="Medium",
            allocation_status="Use reference / portal",
            authority_status="Not Sent",
        )
    else:
        ib.complaint_or_request_flag = "neither"
        ib.department_allocation_status = "not_applicable"
        ib.frontend_status = FrontendStatusPayload(
            title="Chat",
            subtitle="General",
            chat_type="General",
            priority_badge="—",
            allocation_status="Not applicable",
            authority_status="Not Sent",
        )

    _fill_frontend_timeline(ib)
    return ib
