"""Civic taxonomy: domains, services, and complaints for routing and guidance.

This is guidance-only data: we do not perform official government actions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Each domain groups related services and complaints with keyword hints for rule routing.
CIVIC_DOMAINS: List[Dict[str, Any]] = [
    {
        "id": "identity_documents",
        "title": "Identity & Document Services",
        "services": [
            {"id": "aadhaar_update_address", "title": "Aadhaar — update address", "keywords": ["aadhaar", "address", "update address"]},
            {"id": "aadhaar_mobile", "title": "Aadhaar — update mobile", "keywords": ["aadhaar", "mobile", "phone number"]},
            {"id": "aadhaar_download", "title": "Aadhaar — download e-Aadhaar", "keywords": ["download aadhaar", "e-aadhaar"]},
            {"id": "pan_new", "title": "PAN — apply new", "keywords": ["new pan", "apply pan"]},
            {"id": "pan_update", "title": "PAN — update / correction", "keywords": ["update pan", "pan correction"]},
            {"id": "passport_apply", "title": "Passport — new application", "keywords": ["apply passport", "new passport"]},
            {"id": "passport_renew", "title": "Passport — renewal", "keywords": ["renew passport", "passport renewal"]},
            {"id": "dl_apply", "title": "Driving licence — apply", "keywords": ["driving license", "learner licence", "dl apply"]},
            {"id": "dl_renew", "title": "Driving licence — renew", "keywords": ["renew dl", "driving licence renew"]},
            {"id": "voter_apply", "title": "Voter ID — new registration", "keywords": ["voter id", "electoral roll"]},
            {"id": "voter_correction", "title": "Voter ID — correction", "keywords": ["voter correction", "wrong name voter"]},
        ],
        "complaints": [
            {"id": "aadhaar_not_updating", "title": "Aadhaar update not reflecting", "keywords": ["aadhaar not updated", "aadhaar pending"]},
            {"id": "pan_rejected", "title": "PAN application rejected", "keywords": ["pan rejected", "pan application failed"]},
            {"id": "passport_delay", "title": "Passport delay", "keywords": ["passport delayed", "passport status"]},
            {"id": "dl_slot", "title": "DL test slot unavailable", "keywords": ["dl slot", "driving test slot"]},
            {"id": "voter_wrong_details", "title": "Wrong details on voter ID", "keywords": ["wrong voter", "voter id mistake"]},
        ],
    },
    {
        "id": "utilities_municipal",
        "title": "Utilities & Municipal Services",
        "services": [
            {
                "id": "water_connection",
                "title": "Water connection",
                "keywords": [
                    "new water connection",
                    "water supply connection",
                    "water connection",
                    "apply for water",
                    "water meter",
                    "new water supply",
                    "connection for water",
                    "house water connection",
                ],
            },
            {
                "id": "electricity_connection",
                "title": "Electricity connection",
                "keywords": [
                    "new electricity connection",
                    "electricity connection",
                    "power connection",
                    "apply electricity",
                    "kseb connection",
                    "bijli connection",
                    "new meter",
                    "electricity meter",
                ],
            },
            {"id": "waste_management", "title": "Waste management services", "keywords": ["waste pickup", "door to door garbage"]},
            {"id": "property_tax", "title": "Property tax payment", "keywords": ["property tax", "house tax pay"]},
            {"id": "sewage_connection", "title": "Sewage connection", "keywords": ["sewage", "drainage connection"]},
        ],
        "complaints": [
            {
                "id": "water_shortage",
                "title": "Water shortage",
                "keywords": [
                    "no water",
                    "water shortage",
                    "pani nahi",
                    "water not coming",
                    "supply stopped",
                    "no supply",
                    "water supply issue",
                    "water supply problem",
                    "water issue",
                ],
            },
            {"id": "water_leak", "title": "Water leakage", "keywords": ["water leak", "pipeline leak", "water pipe"]},
            {
                "id": "power_cut",
                "title": "Power cut / outage",
                "keywords": [
                    "power cut",
                    "electricity gone",
                    "blackout",
                    "no electricity",
                    "no power",
                    "current gone",
                    "bijli nahi",
                    "electricity issue",
                    "power issue",
                ],
            },
            {"id": "streetlight", "title": "Streetlight not working", "keywords": ["streetlight", "street light", "lamp post"]},
            {"id": "garbage_not_collected", "title": "Garbage not collected", "keywords": ["garbage not collected", "waste not picked"]},
            {"id": "drain_block", "title": "Drain blockage", "keywords": ["drain blocked", "sewage overflow"]},
        ],
    },
    {
        "id": "law_safety",
        "title": "Law & Safety",
        "services": [
            {"id": "police_complaint", "title": "Police complaint registration", "keywords": ["police complaint", "register complaint police"]},
            {"id": "fir_online", "title": "FIR / online police report", "keywords": ["fir", "online fir"]},
            {"id": "cybercrime_report", "title": "Cybercrime reporting", "keywords": ["cyber crime", "1930", "cybercrime portal"]},
            {"id": "traffic_violation", "title": "Traffic violation reporting", "keywords": ["traffic violation", "challan wrong"]},
        ],
        "complaints": [
            {"id": "theft", "title": "Theft", "keywords": ["theft", "stolen", "chori"]},
            {"id": "harassment", "title": "Harassment", "keywords": ["harassment", "threat"]},
            {"id": "online_fraud", "title": "Online fraud", "keywords": ["online fraud", "money taken online"]},
            {"id": "cyber_scam", "title": "Cyber scam", "keywords": ["cyber scam", "fake link"]},
            {"id": "unsafe_area", "title": "Unsafe area", "keywords": ["unsafe area", "dangerous locality"]},
            {"id": "traffic_issue", "title": "Traffic violation / congestion issue", "keywords": ["traffic jam", "wrong fine"]},
        ],
    },
    {
        "id": "financial_tax",
        "title": "Financial & Tax Services",
        "services": [
            {"id": "itr_filing", "title": "Income tax filing", "keywords": ["itr", "income tax filing"]},
            {"id": "gst_registration", "title": "GST registration", "keywords": ["gst registration", "gst apply"]},
            {"id": "govt_loan_schemes", "title": "Government loan schemes", "keywords": ["mudra", "government loan scheme"]},
            {"id": "subsidy_apply", "title": "Subsidy applications", "keywords": ["subsidy apply", "scheme subsidy"]},
        ],
        "complaints": [
            {"id": "tax_refund_delay", "title": "Tax refund delay", "keywords": ["refund delay", "itr refund"]},
            {"id": "wrong_deduction", "title": "Wrong TDS / deduction", "keywords": ["wrong tds", "wrong deduction"]},
            {"id": "loan_rejection", "title": "Loan rejection dispute", "keywords": ["loan rejected", "loan denial"]},
            {"id": "subsidy_not_received", "title": "Subsidy not received", "keywords": ["subsidy not received", "pm kisan pending"]},
        ],
    },
    {
        "id": "social_welfare",
        "title": "Social Welfare & Schemes",
        "services": [
            {"id": "ration_card", "title": "Ration card services", "keywords": ["ration card", "nfsa"]},
            {"id": "pension", "title": "Pension schemes", "keywords": ["pension", "old age pension"]},
            {"id": "scholarship", "title": "Scholarship schemes", "keywords": ["scholarship", "education scholarship"]},
            {"id": "pmay", "title": "PMAY housing", "keywords": ["pmay", "housing scheme"]},
            {"id": "pm_kisan", "title": "PM-Kisan", "keywords": ["pm kisan", "farmer installment"]},
        ],
        "complaints": [
            {"id": "ration_not_received", "title": "Ration not received", "keywords": ["ration not received", "no ration"]},
            {"id": "pension_delay", "title": "Pension delay", "keywords": ["pension delay", "pension pending"]},
            {"id": "scholarship_pending", "title": "Scholarship pending", "keywords": ["scholarship pending", "scholarship status"]},
            {"id": "eligibility_issue", "title": "Eligibility / documentation issue", "keywords": ["not eligible", "scheme rejected"]},
        ],
    },
    {
        "id": "healthcare",
        "title": "Healthcare",
        "services": [
            {"id": "gov_hospital", "title": "Government hospital services", "keywords": ["government hospital", "govt hospital"]},
            {"id": "health_card", "title": "Health card / AB-PMJAY", "keywords": ["ayushman", "health card", "pmjay"]},
            {"id": "vaccination", "title": "Vaccination booking", "keywords": ["vaccination", "immunization slot"]},
        ],
        "complaints": [
            {"id": "no_doctors", "title": "No doctors available", "keywords": ["no doctor", "doctor not available"]},
            {"id": "medicine_shortage", "title": "Medicine shortage", "keywords": ["medicine shortage", "no medicine hospital"]},
            {"id": "poor_service_hospital", "title": "Poor hospital service", "keywords": ["hospital service bad", "staff rude hospital"]},
            {"id": "long_wait", "title": "Long waiting time", "keywords": ["long wait", "queue hospital"]},
        ],
    },
    {
        "id": "transport_infra",
        "title": "Transport & Public Infrastructure",
        "services": [
            {"id": "public_transport_pass", "title": "Public transport pass", "keywords": ["bus pass", "metro pass"]},
            {"id": "metro_card", "title": "Metro card", "keywords": ["metro card", "smart card metro"]},
            {"id": "toll_services", "title": "Toll / FASTag", "keywords": ["fastag", "toll issue"]},
        ],
        "complaints": [
            {"id": "road_damage", "title": "Road damage", "keywords": ["road damage", "bad road"]},
            {"id": "potholes", "title": "Potholes", "keywords": ["pothole", "potholes"]},
            {"id": "traffic_congestion", "title": "Traffic congestion", "keywords": ["traffic congestion", "traffic jam daily"]},
            {"id": "poor_public_transport", "title": "Poor public transport", "keywords": ["bus not on time", "bus overcrowded"]},
        ],
    },
    {
        "id": "education",
        "title": "Education",
        "services": [
            {"id": "school_admission", "title": "School admission", "keywords": ["school admission", "rte admission"]},
            {"id": "college_admission", "title": "College admission", "keywords": ["college admission", "university seat"]},
            {"id": "certificate_issue", "title": "Certificate issuance", "keywords": ["marksheet", "transfer certificate"]},
            {"id": "exam_registration", "title": "Exam registration", "keywords": ["board exam", "exam registration"]},
        ],
        "complaints": [
            {"id": "admission_issue", "title": "Admission issues", "keywords": ["admission denied", "seat issue"]},
            {"id": "certificate_delay", "title": "Certificate delay", "keywords": ["certificate delay", "marksheet pending"]},
            {"id": "exam_error", "title": "Exam errors", "keywords": ["wrong marks", "exam error"]},
        ],
    },
    {
        "id": "digital_online",
        "title": "Digital & Online Services",
        "services": [
            {"id": "digilocker", "title": "DigiLocker", "keywords": ["digilocker", "digital locker"]},
            {"id": "edistrict", "title": "eDistrict services", "keywords": ["edistrict", "e district"]},
            {"id": "online_certificate", "title": "Online certificates", "keywords": ["online certificate", "download certificate"]},
            {"id": "gov_portal", "title": "Government portals", "keywords": ["government portal", "website government"]},
        ],
        "complaints": [
            {"id": "website_down", "title": "Website not working", "keywords": ["website down", "portal not loading"]},
            {"id": "login_issue", "title": "Login issues", "keywords": ["cannot login", "otp not received portal"]},
            {"id": "payment_failure", "title": "Payment failure", "keywords": ["payment failed", "double charged"]},
            {"id": "data_mismatch", "title": "Data mismatch online", "keywords": ["wrong details portal", "data mismatch"]},
        ],
    },
]

COMPLIANCE_DISCLAIMER = (
    "CivicSafe AI provides guidance only. It cannot submit forms, verify identity, or complete official "
    "transactions on your behalf. Use official portals, helplines, or in-person centres for regulated steps."
)


def uses_service_items(parent: str) -> bool:
    """Application / permit path uses the same item lists as legacy 'service' parent."""
    return parent in ("service", "request")


def domain_by_id(domain_id: str) -> Optional[Dict[str, Any]]:
    for d in CIVIC_DOMAINS:
        if d["id"] == domain_id:
            return d
    return None


def find_best_domain_item(
    text: str, parent: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    """Return (domain, item, kind) where kind is service|complaint."""
    lowered = text.lower()
    best: Tuple[float, Optional[Dict[str, Any]], Optional[Dict[str, Any]], str] = (0.0, None, None, "service")
    for dom in CIVIC_DOMAINS:
        if uses_service_items(parent):
            items = dom["services"]
            kind = "service"
        else:
            items = dom["complaints"]
            kind = "complaint"
        for item in items:
            score = sum(1 for kw in item["keywords"] if kw in lowered)
            if score > best[0]:
                best = (float(score), dom, item, kind)
    if best[0] > 0:
        return best[1], best[2], best[3]
    return None, None, "service"


def list_domains_for_parent(parent: str) -> List[Dict[str, str]]:
    out = []
    for dom in CIVIC_DOMAINS:
        if uses_service_items(parent) and dom["services"]:
            out.append({"id": dom["id"], "title": dom["title"]})
        if parent == "complaint" and dom["complaints"]:
            out.append({"id": dom["id"], "title": dom["title"]})
    return out


def list_items(domain_id: str, parent: str) -> List[Dict[str, str]]:
    dom = domain_by_id(domain_id)
    if not dom:
        return []
    key = "services" if uses_service_items(parent) else "complaints"
    return [{"id": x["id"], "title": x["title"]} for x in dom.get(key, [])]


def get_item_detail(domain_id: str, item_id: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], str]]:
    dom = domain_by_id(domain_id)
    if not dom:
        return None
    for it in dom["services"]:
        if it["id"] == item_id:
            return dom, it, "service"
    for it in dom["complaints"]:
        if it["id"] == item_id:
            return dom, it, "complaint"
    return None
