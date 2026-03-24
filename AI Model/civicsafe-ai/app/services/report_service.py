from typing import Any

from app.models import AnalyzeResponse


def build_json_report(raw_text: str, analysis: AnalyzeResponse) -> dict[str, Any]:
    processing_steps = [
        "Input received",
        "Intent classified",
        "Complaint structured",
        "Scam risk analyzed",
        "Cluster key generated",
        "Confidence computed",
    ]
    confidence_summary = round(
        (
            analysis.confidence.intent_confidence
            + analysis.confidence.structure_confidence
            + analysis.confidence.scam_confidence
        )
        / 3,
        3,
    )
    return {
        "input_data": {"raw_text": raw_text},
        "intent_analysis": analysis.intent.model_dump(),
        "structured_data": analysis.structured_data.model_dump(),
        "processing_steps": processing_steps,
        "cluster_info": analysis.cluster_info.model_dump(),
        "decision_explanation": (
            "The system combines multilingual NLP extraction, intent classification, and scam heuristics/LLM analysis "
            "to produce structured civic intelligence output."
        ),
        "confidence_summary": confidence_summary,
    }


def build_markdown_report(json_report: dict[str, Any]) -> str:
    return f"""# CivicSafe AI Report

## Input
{json_report["input_data"]}

## Intent
{json_report["intent_analysis"]}

## Structured Data
{json_report["structured_data"]}

## Steps
{chr(10).join(f"- {step}" for step in json_report["processing_steps"])}

## Cluster
{json_report["cluster_info"]}

## Decision
{json_report["decision_explanation"]}

## Confidence
{json_report["confidence_summary"]}
"""
