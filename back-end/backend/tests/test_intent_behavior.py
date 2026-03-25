"""Unit tests for intent classification heuristics and escalation counting."""

import unittest

from civicsafe_brain.escalation_store import (
    count_similar,
    normalize_issue,
    normalize_region,
    record_signal,
    reset_for_tests,
)
from civicsafe_brain.intent_behavior import _escalation_from_counts, analyze_intent_behavior


class TestEscalationStore(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()

    def test_normalize(self) -> None:
        self.assertEqual(normalize_region("Ward 8"), "ward_8")
        self.assertEqual(normalize_issue("Garbage / Waste"), "garbage_waste")

    def test_repeat_threshold(self) -> None:
        for _ in range(5):
            record_signal("Ward 8", "sanitation_garbage")
        self.assertGreaterEqual(count_similar("Ward 8", "sanitation_garbage", days=7), 5)


class TestIntentHeuristics(unittest.TestCase):
    def test_greeting_is_general(self) -> None:
        r = analyze_intent_behavior("hi", record_complaint_signal=False)
        self.assertEqual(r.detected_intent, "general_conversation")
        self.assertIn("timeline", r.frontend_status.model_dump())

    def test_uncertain_short_reply(self) -> None:
        r = analyze_intent_behavior("I don't know", record_complaint_signal=False)
        self.assertEqual(r.detected_intent, "general_conversation")

    def test_fallback_without_llm_complaint_shape(self) -> None:
        # When no API key, _llm_classify is None and rule fallback runs.
        r = analyze_intent_behavior(
            "the street light is dead near my house in ward 4",
            record_complaint_signal=False,
        )
        self.assertIn(r.detected_intent, ("complaint", "emergency", "query", "request"))


class TestEscalationRules(unittest.TestCase):
    def test_garbage_cluster(self) -> None:
        g, _, pri = _escalation_from_counts("sanitation_garbage", 5, 0)
        self.assertTrue(g)
        self.assertEqual(pri, "high")

    def test_electric_window(self) -> None:
        g, _, pri = _escalation_from_counts("electricity_power", 0, 4)
        self.assertTrue(g)
        self.assertEqual(pri, "high")


if __name__ == "__main__":
    unittest.main()
