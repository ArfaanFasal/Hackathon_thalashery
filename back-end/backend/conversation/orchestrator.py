"""Chat-first civic helpdesk orchestration (stages A–E) with rules + LLM polish + retrieval."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from civicsafe_brain import ai_service as brain
from civicsafe_brain import intent_behavior as ibm
from conversation import store
from knowledge.retrieval import get_index
from models import (
    ChatResponse,
    ComplaintRequest,
    QuickReply,
    ScamBanner,
    ScamRequest,
    ServiceGuidanceRequest,
    SummaryCard,
    SummaryCardField,
)
from services import analyze_complaint, analyze_scam, service_guidance
from taxonomy import (
    COMPLIANCE_DISCLAIMER,
    domain_by_id,
    find_best_domain_item,
    get_item_detail,
    list_domains_for_parent,
    list_items,
    uses_service_items,
)

INFO_KEYWORDS = [
    "statistics",
    "data",
    "gdp",
    "income",
    "climate",
    "employment",
    "nsva",
    "bhim",
    "digital india",
    "net state",
    "how many",
    "report",
    "dataset",
    "indicator",
    "economy",
]

SCAM_TRIGGERS = [
    "otp",
    "upi",
    "pin",
    "verify account",
    "click here",
    "lottery",
    "prize",
    "phishing",
    "fake job",
    "processing fee",
    "bank blocked",
    "kyc link",
]

VAGUE_HINTS = [
    "issue",
    "problem",
    "help",
    "something wrong",
    "government",
    "not sure",
    "documents",
    "trick",
    "scammed",
    "my area",
    "anything",
]

REQUEST_QUESTIONNAIRES: Dict[str, Dict[str, Any]] = {
    "aadhaar_update": {
        "title": "Aadhaar Address Update",
        "questions": [
            {"id": "aadhaar_number", "label": "What is your current Aadhaar number?"},
            {"id": "new_address", "label": "What is the new address you want to update?"},
            {
                "id": "address_proof",
                "label": "Do you have valid address proof (like electricity bill, rental agreement)?",
            },
            {"id": "mobile_linked", "label": "Is your mobile number linked with Aadhaar?"},
            {"id": "mode", "label": "Do you want to update online or visit a nearby Aadhaar center?"},
        ],
    },
    "pan_application": {
        "title": "PAN Card Application",
        "questions": [
            {"id": "full_name", "label": "What is your full name (as per documents)?"},
            {"id": "dob", "label": "What is your date of birth?"},
            {"id": "id_proof", "label": "Do you have identity proof (Aadhaar / Passport / Voter ID)?"},
            {"id": "address", "label": "What is your current address?"},
            {"id": "pan_type", "label": "Do you want an e-PAN or physical PAN card?"},
        ],
    },
    "electricity_connection": {
        "title": "New Electricity Connection",
        "questions": [
            {"id": "connection_type", "label": "What type of connection do you need (residential/commercial)?"},
            {"id": "location", "label": "What is the location/address for the connection?"},
            {"id": "property_proof", "label": "Do you have property ownership or rental proof?"},
            {"id": "load_capacity", "label": "What load capacity do you require (basic/home/heavy usage)?"},
            {"id": "docs_ready", "label": "Do you have identity proof and address proof ready?"},
        ],
    },
    "passport_application": {
        "title": "Passport Application",
        "questions": [
            {"id": "passport_type", "label": "What type of passport do you need (new/renewal)?"},
            {"id": "full_name_dob", "label": "What is your full name and date of birth?"},
            {"id": "identity_docs", "label": "Do you have proof of identity and address?"},
            {"id": "police_verification", "label": "Is police verification already done or required?"},
            {"id": "appointment_city", "label": "Which city do you want to schedule your passport appointment in?"},
        ],
    },
    "driving_licence_application": {
        "title": "Driving License Application",
        "questions": [
            {"id": "learner_license", "label": "Do you already have a learner’s license?"},
            {"id": "vehicle_type", "label": "What type of vehicle license are you applying for?"},
            {"id": "age_dob", "label": "What is your age and date of birth?"},
            {"id": "docs_ready", "label": "Do you have required documents (ID + address proof)?"},
        ],
    },
}

REQUEST_ITEM_TO_FLOW: Dict[str, str] = {
    "aadhaar_update_address": "aadhaar_update",
    "aadhaar_mobile": "aadhaar_update",
    "pan_new": "pan_application",
    "electricity_connection": "electricity_connection",
    "passport_apply": "passport_application",
    "passport_renew": "passport_application",
    "dl_apply": "driving_licence_application",
    "dl_renew": "driving_licence_application",
}


def _utility_path_prefers_request(text: str) -> bool:
    """New connection / application phrasing for water or power → request, not outage complaint."""
    low = text.lower()
    util = any(u in low for u in ("water", "electric", "electricity", "power", "kseb", "bijli"))
    if not util:
        return False
    req_markers = (
        "connection",
        "new meter",
        "apply for",
        "application for",
        "want to apply",
        "need a new",
        "get a new",
        "register for",
        "apply water",
        "apply electricity",
    )
    strong_complaint = any(
        s in low
        for s in (
            "no water",
            "water shortage",
            "not coming",
            "power cut",
            "no electricity",
            "no power",
            "blackout",
            "leak",
            "outage",
            "gone ",
            "not working",
            "garbage",
        )
    )
    if strong_complaint and not any(m in low for m in req_markers):
        return False
    return any(m in low for m in req_markers) or ("connection" in low and util)


def _tokenize_domain_guess(text: str) -> bool:
    t = text.lower()
    for d in list_domains_for_parent("request") + list_domains_for_parent("complaint"):
        if d["id"].replace("_", " ") in t or d["title"].lower() in t:
            return True
    return False


def _is_vague(text: str) -> bool:
    m = text.strip().lower()
    if len(m) < 12:
        return True
    if any(v in m for v in VAGUE_HINTS) and len(m) < 120:
        return True
    _, s_item, _ = find_best_domain_item(m, "request")
    _, c_item, _ = find_best_domain_item(m, "complaint")
    if s_item or c_item:
        return False
    if _tokenize_domain_guess(m):
        return False
    return len(m) < 90


def _info_intent(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in INFO_KEYWORDS)


def _infer_parent(text: str) -> Optional[str]:
    if _info_intent(text):
        return "info"
    low = text.lower()
    if any(s in low for s in SCAM_TRIGGERS) or "scam" in low or "fraud" in low:
        return "scam"
    intent = brain.analyze_intent(text)
    if intent.intent == "scam_report":
        return "scam"
    if intent.intent == "service_guidance":
        return "request"
    if intent.intent == "complaint_report":
        return "complaint"
    if intent.intent == "general_query":
        return "info"
    _, s_item, _ = find_best_domain_item(low, "request")
    _, c_item, _ = find_best_domain_item(low, "complaint")
    if s_item and not c_item:
        return "request"
    if c_item and not s_item:
        return "complaint"
    if s_item and c_item:
        return None
    return None


def _match_domain_from_text(text: str, parent: str) -> Optional[str]:
    low = text.lower()
    for d in list_domains_for_parent(parent):
        if d["id"] in low or d["title"].lower() in low:
            return d["id"]
    return None


def _match_item_from_text(domain_id: str, parent: str, text: str) -> Optional[str]:
    dom = domain_by_id(domain_id)
    if not dom:
        return None
    low = text.lower()
    key = "services" if uses_service_items(parent) else "complaints"
    for it in dom[key]:
        if any(kw in low for kw in it["keywords"]) or it["id"].replace("_", " ") in low:
            return it["id"]
    return None


def _next_missing_slot(slots: Dict[str, str], parent: str) -> Optional[str]:
    order = ["description", "location", "urgency", "since_when"]
    for k in order:
        if not (slots.get(k) or "").strip():
            if parent == "scam" and k in {"location", "urgency", "since_when"}:
                continue
            return k
    return None


def _slot_prompt(slot: str, user_context: str) -> str:
    kind = {
        "description": "need_detail",
        "location": "need_location",
        "urgency": "need_urgency",
        "since_when": "need_since",
    }.get(slot, "need_detail")
    return brain.conversational_nudge(user_context or "…", kind)


def _ensure_chat_state(state: Dict[str, Any]) -> None:
    state.setdefault("chat_mode", "free")
    state.setdefault("request_flow", None)
    state.setdefault("request_answers", {})
    state.setdefault("request_question_index", 0)
    state.setdefault("request_current_item", None)


def _ensure_request_questionnaire(state: Dict[str, Any]) -> bool:
    item_id = state.get("item_id")
    if not item_id:
        return False
    flow_key = REQUEST_ITEM_TO_FLOW.get(item_id)
    if not flow_key or flow_key not in REQUEST_QUESTIONNAIRES:
        return False
    if state.get("request_current_item") != item_id:
        state["request_flow"] = flow_key
        state["request_answers"] = {}
        state["request_question_index"] = 0
        state["request_current_item"] = item_id
    return True


def _request_question_label(state: Dict[str, Any], idx: int) -> Optional[str]:
    flow = state.get("request_flow")
    if not flow or flow not in REQUEST_QUESTIONNAIRES:
        return None
    questions = REQUEST_QUESTIONNAIRES[flow]["questions"]
    if idx < 0 or idx >= len(questions):
        return None
    return str(questions[idx]["label"])


def _apply_quick_reply(state: Dict[str, Any], qid: str) -> None:
    if qid == "qr_skip_slot":
        if state.get("parent") == "request" and _ensure_request_questionnaire(state):
            state["request_question_index"] = int(state.get("request_question_index") or 0) + 1
            return
        missing = _next_missing_slot(state["slots"], state.get("parent") or "complaint")
        if missing:
            state["slots"][missing] = "Not specified"
        return
    if qid.startswith("qr_intent_"):
        state["chat_mode"] = "civic"
        raw_parent = qid.replace("qr_intent_", "")
        state["parent"] = "request" if raw_parent == "service" else raw_parent
        if state["parent"] == "info":
            state["stage"] = "E"
        elif state["parent"] == "scam":
            state["stage"] = "D"
        else:
            state["stage"] = "B"
        return
    if qid.startswith("qr_domain_"):
        state["chat_mode"] = "civic"
        state["domain_id"] = qid.replace("qr_domain_", "")
        state["stage"] = "C"
        return
    if qid.startswith("qr_item_"):
        state["chat_mode"] = "civic"
        state["item_id"] = qid.replace("qr_item_", "")
        state["stage"] = "D"
        return
    if qid == "qr_new_case":
        state.update(
            {
                "stage": "A",
                "parent": None,
                "domain_id": None,
                "item_id": None,
                "item_kind": None,
                "slots": {"description": "", "location": "", "urgency": "", "since_when": ""},
                "chat_mode": "free",
                "request_flow": None,
                "request_answers": {},
                "request_question_index": 0,
                "request_current_item": None,
            }
        )


def _maybe_scam_banner(text: str) -> Optional[ScamBanner]:
    low = text.lower()
    if not any(s in low for s in SCAM_TRIGGERS) and "scam" not in low:
        return None
    sa = brain.analyze_scam(text)
    show = sa.scam_detected or any(s in low for s in ["otp", "upi", "phishing"])
    if not show:
        return ScamBanner(show=False)
    return ScamBanner(
        show=True,
        risk_level=sa.risk_level.title() if sa.risk_level else "Medium",
        headline="Possible scam or risky message pattern",
        advice=sa.recommendation,
        escalation="For cyber fraud in India, consider reporting via the National Cybercrime Reporting Portal or helpline 1930. Do not share OTPs, UPI PINs, or card details.",
    )


def _finalize(state: Dict[str, Any], last_user_text: str) -> Tuple[str, Optional[SummaryCard], bool]:
    parent = state["parent"]
    slots = state["slots"]
    desc = (slots.get("description") or last_user_text or "").strip()
    loc = (slots.get("location") or "Not specified").strip()
    urg = (slots.get("urgency") or "Medium").strip()

    if parent == "info":
        hits = get_index().search(last_user_text or desc, top_k=4)
        lines = []
        for h in hits:
            lines.append(f"• ({h['theme']}) {h['snippet']}")
        body = (
            "Here is what we found in the indexed public datasets that might relate to your question:\n\n"
            + (
                "\n".join(lines)
                if lines
                else "No close match in the local dataset index. Try rephrasing or naming a state, sector, or topic (for example NSVA, climate, BHIM)."
            )
        )
        body += f"\n\n{COMPLIANCE_DISCLAIMER}"
        card = SummaryCard(
            title="Knowledge snapshot",
            subtitle="Dataset-backed snippets (demo index)",
            fields=[SummaryCardField(label="Sources", value=", ".join({h['source'] for h in hits}) or "—")],
            badges=["Informational"],
            next_steps=[
                "Verify figures on the original government or open-data portal.",
                "Ask a follow-up with a specific state or year if you have one.",
            ],
        )
        return body, card, True

    if parent == "scam":
        payload = desc or last_user_text
        res = analyze_scam(ScamRequest(text=payload))
        msg = (
            f"We've reviewed what you shared. Estimated risk level: **{res.risk_level}** (heuristic score {res.scam_probability}/100).\n\n"
            f"{res.reason}\n\n"
            f"**Safety tips:** Never share OTPs or UPI PINs. Do not click unknown links. Contact your bank from the official app or number on the card.\n\n"
            f"{COMPLIANCE_DISCLAIMER}"
        )
        card = SummaryCard(
            title="Scam / risk check summary",
            subtitle="Guidance only — not a legal finding",
            fields=[
                SummaryCardField(label="Risk level", value=res.risk_level),
                SummaryCardField(label="Case reference", value=res.record_id),
            ],
            badges=["Scam shield"],
            next_steps=[
                "Screenshot the message (redact personal data) for your records.",
                "Report via official cybercrime channels if you lost money or shared credentials.",
            ],
        )
        return msg, card, True

    detail: Optional[Tuple[Any, ...]] = None
    title = "Civic case summary"
    if state.get("domain_id") and state.get("item_id"):
        detail = get_item_detail(state["domain_id"], state["item_id"])
    if detail:
        _, it, _kind = detail
        title = it["title"]
        full_text = f"{it['title']}. {desc} Location: {loc}. Urgency: {urg}. Since: {slots.get('since_when') or 'unspecified'}."
    else:
        full_text = f"{desc} Location: {loc}. Urgency: {urg}."

    if parent in ("request", "service"):
        request_answers = state.get("request_answers") or {}
        if request_answers:
            qa_lines = "\n".join(f"{k}: {v}" for k, v in request_answers.items())
            full_text = f"{full_text}\nRequest details:\n{qa_lines}"
        out = service_guidance(
            ServiceGuidanceRequest(
                text=full_text,
                language="auto",
                service_category="auto",
                taxonomy_domain_id=state.get("domain_id"),
                taxonomy_item_id=state.get("item_id"),
            )
        )
        steps = out.get("steps") or []
        docs = out.get("documents_required") or []
        msg = (
            f"**{str(out.get('service_name', 'service')).title()} readiness**\n\n"
            f"{out.get('readiness_summary', '')}\n\n"
            f"**Suggested documents:** {', '.join(docs[:6])}\n\n"
            f"**Steps:**\n"
            + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps[:8]))
            + f"\n\nOfficial: {out.get('official_website', '')} · Support: {out.get('support_channel', '')}\n\n"
            f"{COMPLIANCE_DISCLAIMER}"
        )
        card = SummaryCard(
            title=title,
            subtitle="Service guidance (not a submission)",
            fields=[
                SummaryCardField(label="Record", value=str(out.get("record_id", "—"))),
                SummaryCardField(label="Portal", value=str(out.get("official_website", "—"))),
            ],
            badges=["Request / application path"],
            next_steps=[
                "Gather documents before visiting the portal or centre.",
                "Complete identity verification only on official websites or authorised centres.",
            ],
        )
        if request_answers:
            for key, value in list(request_answers.items())[:4]:
                card.fields.append(SummaryCardField(label=key, value=str(value)))
        return msg, card, True

    dom_t: Optional[str] = None
    it_t: Optional[str] = None
    if state.get("domain_id") and state.get("item_id"):
        det = get_item_detail(state["domain_id"], state["item_id"])
        if det:
            d, it, _k = det
            dom_t = d.get("title")
            it_t = it.get("title")
    res = analyze_complaint(
        ComplaintRequest(
            text=full_text,
            language="auto",
            complaint_mode="general",
            taxonomy_domain_id=state.get("domain_id"),
            taxonomy_item_id=state.get("item_id"),
            taxonomy_domain_title=dom_t,
            taxonomy_item_title=it_t,
        )
    )
    msg = (
        f"{res.citizen_message}\n\n"
        f"**Issue type:** {res.issue_type}\n"
        f"**Category:** {res.category}\n"
        f"**Department:** {res.department}\n"
        f"**Location:** {res.location}\n"
        f"**Priority:** {res.priority.title()}\n"
        f"**Complaint type:** {res.complaint_type.replace('_', ' ').title()}\n"
        f"**Insight:** {res.insight}\n\n"
        f"**Suggested next step:** Use your municipal or department helpline or online grievance portal with this summary when you file officially.\n\n"
        f"{COMPLIANCE_DISCLAIMER}"
    )
    card = SummaryCard(
        title=title,
        subtitle="Draft summary for official channels",
        fields=[
            SummaryCardField(label="Issue", value=res.issue_type),
            SummaryCardField(label="Department", value=res.department),
            SummaryCardField(label="Location", value=res.location),
            SummaryCardField(label="Priority", value=res.priority.title()),
            SummaryCardField(label="Case ID", value=res.record_id),
        ],
        badges=["Complaint draft"],
        next_steps=[
            "Copy the summary into your city's grievance or department portal.",
            "Attach photos if the portal allows (streetlights, leaks, etc.).",
        ],
    )
    return msg, card, True


def _fill_slot_from_message(state: Dict[str, Any], msg: str) -> None:
    if not msg.strip():
        return
    parent = state.get("parent") or "complaint"
    missing = _next_missing_slot(state["slots"], parent)
    if not missing:
        return
    if missing == "description":
        state["slots"]["description"] = msg.strip()
    elif missing == "location" and len(msg) < 100:
        state["slots"]["location"] = msg.strip()
    elif missing == "urgency" and re.search(r"\b(low|medium|high|critical)\b", msg, re.I):
        state["slots"]["urgency"] = msg.strip()
    elif missing == "since_when":
        state["slots"]["since_when"] = msg.strip()


def process_chat_turn(
    session_id: Optional[str],
    message: str,
    quick_reply_id: Optional[str],
) -> ChatResponse:
    store.init_db()
    msg = (message or "").strip()
    if not session_id or store.get_session(session_id) is None:
        session_id = store.create_session()
    _, state = store.get_session(session_id)
    assert state is not None
    _ensure_chat_state(state)
    parent = state.get("parent") or "complaint"

    log_user = msg
    if quick_reply_id:
        log_user = f"{msg} [{quick_reply_id}]" if msg else f"[{quick_reply_id}]"
    skip_user_log = bool(quick_reply_id and quick_reply_id.startswith("qr_hint_"))
    if (msg or quick_reply_id) and not skip_user_log:
        store.append_message(session_id, "user", log_user)

    if quick_reply_id:
        _apply_quick_reply(state, quick_reply_id)

    scam_banner = _maybe_scam_banner(msg) if msg else None

    assistant = ""
    quick: List[QuickReply] = []
    summary: Optional[SummaryCard] = None
    case_complete = False
    intent_snapshot: Optional[Dict[str, Any]] = None
    chat_signals: Optional[Dict[str, Any]] = None

    # Free-text refinement: match domain/item from combined thread text (fixes "water" follow-ups)
    if msg and not quick_reply_id and state.get("parent") in {"request", "service", "complaint"}:
        comb = f"{state['slots'].get('description') or ''} {msg}".strip()
        low = comb.lower()
        par = state["parent"]
        if state["stage"] == "B" and not state.get("domain_id"):
            dom, item, _k = find_best_domain_item(low, par)
            if dom and item:
                state["domain_id"] = dom["id"]
                state["item_id"] = item["id"]
                state["stage"] = "D"
                state["slots"]["description"] = state["slots"].get("description") or comb
            else:
                dom = _match_domain_from_text(msg, par)
                if dom:
                    state["domain_id"] = dom
                    state["stage"] = "C"
        if state["stage"] == "C" and state.get("domain_id"):
            item = _match_item_from_text(state["domain_id"], par, low)
            if item:
                state["item_id"] = item
                state["stage"] = "D"

    st = state["stage"]  # after quick replies and text refinements

    if st == "A":
        if not msg and not quick_reply_id:
            assistant = brain.free_chat_opening() if state.get("chat_mode") == "free" else brain.conversational_opening()
            quick = [
                QuickReply(id="qr_hint_request", label="Example: Aadhaar update request"),
                QuickReply(id="qr_hint_complaint", label="Example: no water supply"),
                QuickReply(id="qr_hint_scam", label="Example: OTP request"),
            ]
        elif quick_reply_id and quick_reply_id.startswith("qr_hint_"):
            state["chat_mode"] = "civic"
            hints = {
                "qr_hint_request": "I want to update Aadhaar address and need the required documents.",
                "qr_hint_complaint": "There has been no water in our ward for two days.",
                "qr_hint_scam": "Someone messaged asking for my UPI PIN to verify a refund.",
            }
            injected = hints.get(quick_reply_id, "")
            msg = injected
            store.append_message(session_id, "user", injected)
            par = _infer_parent(msg)
            if par:
                state["parent"] = par
                if par == "info":
                    state["stage"] = "E"
                    assistant, summary, case_complete = _finalize(state, msg)
                elif par == "scam":
                    state["stage"] = "D"
                    state["slots"]["description"] = msg
                    assistant = brain.conversational_nudge(msg, "need_detail")
                else:
                    state["stage"] = "B"
                    par_hint = "request" if par == "service" else par
                    dom, item, _k = find_best_domain_item(msg.lower(), par_hint)
                    if dom and item:
                        state["domain_id"] = dom["id"]
                        state["item_id"] = item["id"]
                        state["stage"] = "D"
                        state["slots"]["description"] = msg
                        assistant = brain.conversational_nudge(msg, "after_intent_locked")
                    else:
                        assistant = brain.conversational_nudge(msg, "need_area")
                        quick = [
                            QuickReply(id=f"qr_domain_{d['id']}", label=d["title"])
                            for d in list_domains_for_parent(par_hint)[:6]
                        ]
        elif not quick_reply_id:
            if state.get("chat_mode") == "free":
                low = msg.lower()
                if not (any(s in low for s in SCAM_TRIGGERS) or "scam" in low or "fraud" in low):
                    sig = brain.free_chat_turn_json(msg)
                    chat_signals = {
                        "keywords": sig["keywords"],
                        "civic_signal": sig["civic_signal"],
                        "enter_civic_flow": sig["enter_civic_flow"],
                    }
                    if not sig["enter_civic_flow"]:
                        assistant = sig["reply"]
                        assistant = brain.polish_assistant_message(assistant)
                        store.save_state(session_id, state)
                        store.append_message(session_id, "assistant", assistant)
                        return ChatResponse(
                            session_id=session_id,
                            assistant_message=assistant,
                            quick_replies=[],
                            summary_card=None,
                            scam_banner=scam_banner,
                            case_complete=False,
                            stage=state.get("stage", "A"),
                            intent_analysis=None,
                            frontend_status=None,
                            chat_mode="free",
                            chat_signals=chat_signals,
                        )
                    state["chat_mode"] = "civic"
                    state["reply_preamble"] = sig["reply"]
                else:
                    state["chat_mode"] = "civic"

            low = msg.lower()
            if any(s in low for s in SCAM_TRIGGERS) or "scam" in low or "fraud" in low:
                state["parent"] = "scam"
                state["stage"] = "D"
                state["slots"]["description"] = msg
                ib = ibm.analyze_intent_behavior(msg)
                intent_snapshot = ib.model_dump()
                assistant = brain.conversational_nudge(msg, "need_detail")
            else:
                ib = ibm.analyze_intent_behavior(msg)
                intent_snapshot = ib.model_dump()
                intent = ib.detected_intent
                if intent == "general_conversation":
                    assistant = ib.user_facing_message
                    quick = [
                        QuickReply(id="qr_intent_service", label="Apply for a service / document"),
                        QuickReply(id="qr_intent_complaint", label="Report a civic problem"),
                        QuickReply(id="qr_intent_info", label="Ask how-to or status"),
                    ]
                elif intent == "follow_up":
                    assistant = ib.user_facing_message
                    summary = SummaryCard(
                        title=ib.frontend_status.title or "Follow-up",
                        subtitle=ib.dashboard_status_label,
                        fields=[SummaryCardField(label="Chat type", value="Follow-up / status check")],
                        badges=["Follow-up"],
                        next_steps=[
                            "Keep your acknowledgement or complaint number handy when you call the helpline.",
                            "Check the department portal's grievance section for updates.",
                        ],
                    )
                    case_complete = True
                elif intent == "query":
                    state["parent"] = "info"
                    state["stage"] = "E"
                    assistant, summary, case_complete = _finalize(state, msg)
                elif intent == "request":
                    state["parent"] = "request"
                    state["stage"] = "B"
                    dom, item, _k = find_best_domain_item(msg.lower(), "request")
                    if dom and item:
                        state["domain_id"] = dom["id"]
                        state["item_id"] = item["id"]
                        state["stage"] = "D"
                        state["slots"]["description"] = msg
                        assistant = brain.conversational_nudge(msg, "after_intent_locked")
                    else:
                        assistant = ib.user_facing_message
                        quick = [
                            QuickReply(id=f"qr_domain_{d['id']}", label=d["title"])
                            for d in list_domains_for_parent("request")[:6]
                        ]
                elif intent in ("complaint", "emergency") and _utility_path_prefers_request(msg):
                    state["parent"] = "request"
                    state["stage"] = "B"
                    dom, item, _k = find_best_domain_item(msg.lower(), "request")
                    if dom and item:
                        state["domain_id"] = dom["id"]
                        state["item_id"] = item["id"]
                        state["stage"] = "D"
                        state["slots"]["description"] = msg
                        assistant = brain.conversational_nudge(msg, "after_intent_locked")
                    else:
                        assistant = ib.user_facing_message
                        quick = [
                            QuickReply(id=f"qr_domain_{d['id']}", label=d["title"])
                            for d in list_domains_for_parent("request")[:6]
                        ]
                elif intent in ("complaint", "emergency"):
                    state["parent"] = "complaint"
                    state["stage"] = "B"
                    if intent == "emergency":
                        state["slots"]["urgency"] = "high"
                    dom, item, _k = find_best_domain_item(msg.lower(), "complaint")
                    if dom and item:
                        state["domain_id"] = dom["id"]
                        state["item_id"] = item["id"]
                        state["stage"] = "D"
                        state["slots"]["description"] = msg
                        assistant = brain.conversational_nudge(msg, "after_intent_locked")
                    else:
                        assistant = ib.user_facing_message
                        quick = [
                            QuickReply(id=f"qr_domain_{d['id']}", label=d["title"])
                            for d in list_domains_for_parent("complaint")[:6]
                        ]
                else:
                    state["parent"] = "info"
                    state["stage"] = "E"
                    assistant, summary, case_complete = _finalize(state, msg)

        pre = state.pop("reply_preamble", None)
        if pre and assistant:
            assistant = f"{pre}\n\n{assistant}"

    elif st == "B":
        if not state.get("domain_id"):
            assistant = brain.conversational_nudge(msg, "need_area")
            quick = [
                QuickReply(id=f"qr_domain_{d['id']}", label=d["title"])
                for d in list_domains_for_parent(state["parent"])
            ]
        else:
            state["stage"] = "C"
            assistant = brain.conversational_nudge(state["slots"].get("description") or msg, "pick_item")
            quick = [
                QuickReply(id=f"qr_item_{it['id']}", label=it["title"])
                for it in list_items(state["domain_id"], state["parent"])[:10]
            ]

    elif st == "C":
        if not state.get("domain_id"):
            state["stage"] = "B"
            assistant = brain.conversational_nudge(msg, "need_area")
            quick = [
                QuickReply(id=f"qr_domain_{d['id']}", label=d["title"])
                for d in list_domains_for_parent(state["parent"])
            ]
        else:
            assistant = brain.conversational_nudge(state["slots"].get("description") or msg, "pick_item")
            quick = [
                QuickReply(id=f"qr_item_{it['id']}", label=it["title"])
                for it in list_items(state["domain_id"], state["parent"])[:10]
            ]

    elif st == "D":
        parent = state.get("parent") or "complaint"
        if parent == "request" and _ensure_request_questionnaire(state):
            flow_key = state.get("request_flow")
            flow = REQUEST_QUESTIONNAIRES.get(str(flow_key), {})
            questions = flow.get("questions") or []
            idx = int(state.get("request_question_index") or 0)
            if msg and not str(quick_reply_id or "").startswith("qr_") and idx > 0 and idx - 1 < len(questions):
                q_prev = questions[idx - 1]
                answers = dict(state.get("request_answers") or {})
                answers[str(q_prev["label"])] = msg.strip()
                state["request_answers"] = answers
            if idx < len(questions):
                assistant = str(questions[idx]["label"])
                state["request_question_index"] = idx + 1
                quick = [QuickReply(id="qr_skip_slot", label="Skip for now")]
            else:
                state["stage"] = "E"
                assistant, summary, case_complete = _finalize(state, msg)
        else:
            if quick_reply_id == "qr_skip_slot":
                pass
            elif msg and not str(quick_reply_id or "").startswith("qr_"):
                _fill_slot_from_message(state, msg)
            if parent == "scam" and not state["slots"].get("description") and msg:
                state["slots"]["description"] = msg
            missing = _next_missing_slot(state["slots"], parent)
            if missing:
                ctx = (state["slots"].get("description") or "") + " " + msg
                assistant = _slot_prompt(missing, ctx.strip())
                if missing != "description":
                    quick = [QuickReply(id="qr_skip_slot", label="Skip for now")]
            else:
                state["stage"] = "E"
                assistant, summary, case_complete = _finalize(state, msg)

    elif st == "E":
        assistant, summary, case_complete = _finalize(state, msg)

    if case_complete:
        quick = [QuickReply(id="qr_new_case", label="Start another request")]

    assistant = brain.polish_assistant_message(assistant)

    store.save_state(session_id, state)
    store.append_message(session_id, "assistant", assistant)

    fs = None
    if state.get("chat_mode") == "civic" and intent_snapshot and isinstance(intent_snapshot.get("frontend_status"), dict):
        fs = intent_snapshot["frontend_status"]

    return ChatResponse(
        session_id=session_id,
        assistant_message=assistant,
        quick_replies=quick,
        summary_card=summary,
        scam_banner=scam_banner,
        case_complete=case_complete,
        stage=state.get("stage", "A"),
        intent_analysis=intent_snapshot if state.get("chat_mode") == "civic" else None,
        frontend_status=fs,
        chat_mode=state.get("chat_mode", "free"),
        chat_signals=chat_signals,
    )
