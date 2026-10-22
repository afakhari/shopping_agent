"""Dependency-free unit tests for the local golden-path smoke helper."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("smoke-golden-path.py")
SPEC = importlib.util.spec_from_file_location("golden_path_smoke", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load smoke script at {SCRIPT_PATH}")
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


class GoldenPathHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = {
            "type": "ui.component",
            "payload": {
                "component": "component_stack",
                "data": {
                    "components": [
                        {"type": "category_choice", "data": {"alternative_query": "فشارسنج صنعتی"}},
                        {
                            "type": "product_results",
                            "data": {
                                "query": "فشارسنج",
                                "total": 1,
                                "results": [
                                    {
                                        "product": {"id": "p1", "title": "فشارسنج نمونه"},
                                        "best_offer": {
                                            "id": "o1",
                                            "price_toman": "950000",
                                            "shop": {
                                                "id": "s1",
                                                "name": "فروشگاه نمونه",
                                                "accepts_in_person_credit": False,
                                            },
                                        },
                                    }
                                ],
                            },
                        },
                    ]
                },
            },
        }

    def test_finds_product_results_nested_in_component_stack(self) -> None:
        results = SMOKE.first_results_from_events([self.event])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["best_offer"]["id"], "o1")

    def test_accepts_result_inside_budget(self) -> None:
        results = SMOKE.first_results_from_events([self.event])
        SMOKE.validate_hard_constraints(results, {"max_price_toman": "1000000"})

    def test_rejects_result_over_budget(self) -> None:
        results = SMOKE.first_results_from_events([self.event])
        with self.assertRaises(SMOKE.SmokeFailure):
            SMOKE.validate_hard_constraints(results, {"max_price_toman": "500000"})

    def test_rejects_result_without_required_in_person_credit(self) -> None:
        results = SMOKE.first_results_from_events([self.event])
        with self.assertRaises(SMOKE.SmokeFailure):
            SMOKE.validate_hard_constraints(results, {"must_have_in_person_credit": True})

    def test_llm_diagnostics_does_not_claim_model_is_configured_when_health_field_is_missing(self) -> None:
        state, _ = SMOKE.classify_llm_runtime("heuristic", "unknown", "unknown")
        self.assertEqual(state, "HEURISTIC_FALLBACK_UNDIAGNOSED")

    def test_llm_diagnostics_reports_missing_credentials(self) -> None:
        state, _ = SMOKE.classify_llm_runtime("heuristic", "missing_api_key", "deterministic_fallback")
        self.assertEqual(state, "FALLBACK_UNCONFIGURED")

    def test_llm_diagnostics_distinguishes_configured_but_failed_provider(self) -> None:
        state, _ = SMOKE.classify_llm_runtime("heuristic", "configured", "model_configured")
        self.assertEqual(state, "FALLBACK_AFTER_CONFIG")

    def test_llm_diagnostics_marks_actual_llm_turn_as_active(self) -> None:
        state, _ = SMOKE.classify_llm_runtime("llm", "configured", "model_configured")
        self.assertEqual(state, "ACTIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
