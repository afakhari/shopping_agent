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


    def test_recovery_prefers_real_same_model_offer(self) -> None:
        payload = {
            "alternatives": [{"id": "offer-2", "shop": {"id": "shop-2"}}],
            "alternative_products": [
                {"best_offer": {"id": "offer-3", "shop": {"id": "shop-3"}}}
            ],
        }
        self.assertEqual(
            SMOKE.pick_recovery_offer(payload),
            {"offer_id": "offer-2", "shop_id": "shop-2"},
        )

    def test_recovery_uses_valid_alternative_product_when_same_model_unavailable(self) -> None:
        payload = {
            "alternatives": [],
            "alternative_products": [
                {"best_offer": {"id": "offer-4", "shop": {"id": "shop-4"}}}
            ],
        }
        self.assertEqual(
            SMOKE.pick_recovery_offer(payload),
            {"offer_id": "offer-4", "shop_id": "shop-4"},
        )
        self.assertIsNone(SMOKE.pick_recovery_offer({"alternative_products": []}))

    def test_sse_and_json_use_same_session_aware_transport(self) -> None:
        """Regression: SSE must not bypass the opener that retains session cookies."""
        from unittest.mock import patch

        class Response:
            def __init__(self, status: int, content_type: str, body: bytes) -> None:
                self.status = status
                self.headers = {"Content-Type": content_type}
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self) -> bytes:
                return self.body

        json_response = Response(
            201, "application/json", b'{"mission_id":"test-mission"}'
        )
        sse_response = Response(
            200, "text/event-stream; charset=utf-8",
            b'id: 1\ndata: {"seq":1,"type":"turn.completed","payload":{}}\n\n',
        )
        with patch.object(SMOKE, "_SESSION_OPENER") as opener:
            opener.open.side_effect = [json_response, sse_response]
            code, created, _ = SMOKE.request_json(
                "http://frontend", "/api/v1/missions/",
                method="POST", payload={"initial_message": "test"},
            )
            sse_code, events, _ = SMOKE.post_sse(
                "http://frontend", "/api/v1/missions/test-mission/turns/",
                {"message": "test"},
            )
            self.assertEqual(code, 201)
            self.assertEqual(created["mission_id"], "test-mission")
            self.assertEqual(sse_code, 200)
            self.assertEqual([event["type"] for event in events], ["turn.completed"])
            self.assertEqual(opener.open.call_count, 2)
            self.assertEqual(opener.open.call_args_list[0].args[0].get_method(), "POST")
            self.assertEqual(opener.open.call_args_list[1].args[0].get_header("Accept"), "text/event-stream")


if __name__ == "__main__":
    unittest.main(verbosity=2)
