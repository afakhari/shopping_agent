import io
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.agent.graph import _budget_from_message, _query_from_message, parse_request_node, render_results_node


class MissionRequestParserTests(SimpleTestCase):
    def test_persian_budget_phrase_converts_millions_to_toman(self):
        self.assertEqual(
            _budget_from_message("یک هدفون تا سقف ۳ میلیون تومان می‌خواهم"),
            "3000000",
        )

    def test_query_parser_removes_purchase_filler_and_budget(self):
        self.assertEqual(
            _query_from_message("یک هدفون بی‌سیم تا سقف ۳ میلیون تومان می‌خواهم"),
            "هدفون بی سیم",
        )

    def test_credit_intent_is_preserved_in_structured_constraints(self):
        state = parse_request_node(
            {
                "user_message": "یک هدفون قسطی می‌خواهم",
                "constraints": {"city": "tehran", "must_have_in_person_credit": False},
            }
        )
        self.assertTrue(state["constraints"]["must_have_in_person_credit"])


class IntentPayloadValidationTests(SimpleTestCase):
    def test_intent_payload_is_schema_limited_and_does_not_invent_default_sort(self):
        from apps.agent.llm import validate_intent_payload

        payload = validate_intent_payload(
            {
                "search_query": " هدفون بی‌سیم ",
                "max_price_toman": "۳۰۰۰۰۰۰",
                "must_have_in_person_credit": True,
                "sort": None,
                "extra_fact": "ignore me",
            }
        )
        self.assertEqual(payload["search_query"], "هدفون بی سیم")
        self.assertEqual(payload["max_price_toman"], "3000000")
        self.assertTrue(payload["must_have_in_person_credit"])
        self.assertIsNone(payload["sort"])
        self.assertNotIn("extra_fact", payload)

    def test_invalid_intent_payload_is_rejected(self):
        from apps.agent.llm import validate_intent_payload

        self.assertIsNone(validate_intent_payload({"search_query": "", "must_have_in_person_credit": False}))
        self.assertIsNone(validate_intent_payload("not-json-object"))


class OptionalLLMAdapterTests(SimpleTestCase):
    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="openai_compatible",
        LLM_API_KEY="test-key",
        LLM_MODEL="test-model",
        LLM_BASE_URL="https://llm.example.test/v1",
        LLM_TIMEOUT_SECONDS=2,
    )
    @patch("apps.agent.llm.urlopen")
    def test_valid_provider_response_is_reduced_to_intent_schema(self, mocked_urlopen):
        from apps.agent.llm import extract_intent

        provider_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "search_query": "هدفون بی‌سیم",
                                "max_price_toman": 3000000,
                                "must_have_in_person_credit": True,
                                "sort": "price_asc",
                                "store_name": "hallucinated store",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
        mocked_urlopen.return_value = io.BytesIO(
            json.dumps(provider_payload, ensure_ascii=False).encode("utf-8")
        )

        result = extract_intent("هدفون قسطی تا سقف ۳ میلیون", {"city": "tehran"})

        self.assertEqual(result["search_query"], "هدفون بی سیم")
        self.assertEqual(result["max_price_toman"], "3000000")
        self.assertTrue(result["must_have_in_person_credit"])
        self.assertEqual(result["sort"], "price_asc")
        self.assertNotIn("store_name", result)
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 2)

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="openai",
        LLM_API_KEY="test-key",
        LLM_MODEL="test-model",
        LLM_BASE_URL="https://api.openai.com/v1",
        LLM_TIMEOUT_SECONDS=2,
    )
    @patch("apps.agent.llm.urlopen")
    def test_openai_provider_uses_current_completion_token_field(self, mocked_urlopen):
        from apps.agent.llm import extract_intent

        provider_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "search_query": "فشارسنج",
                                "max_price_toman": None,
                                "must_have_in_person_credit": False,
                                "sort": None,
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }
        mocked_urlopen.return_value = io.BytesIO(json.dumps(provider_payload).encode("utf-8"))
        self.assertEqual(extract_intent("فشارسنج", {"city": "tehran"})["search_query"], "فشارسنج")
        request_body = json.loads(mocked_urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(request_body["max_completion_tokens"], 250)
        self.assertNotIn("max_tokens", request_body)

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="boxapi",
        LLM_API_KEY="test-secret-not-a-real-key",
        LLM_MODEL="gpt-5.4-mini",
        LLM_BASE_URL="https://ai.boxapi.ir/ai/v1",
        LLM_TIMEOUT_SECONDS=15,
    )
    @patch("apps.agent.llm.urlopen")
    def test_boxapi_hackathon_sends_only_documented_chat_fields(self, mocked_urlopen):
        from apps.agent.llm import configuration_diagnostics, extract_intent

        provider_payload = {
            "choices": [{"message": {"content": json.dumps({
                "search_query": "هدفون بی سیم",
                "max_price_toman": 3000000,
                "must_have_in_person_credit": True,
                "sort": None,
            }, ensure_ascii=False)}}]
        }
        mocked_urlopen.return_value = io.BytesIO(
            json.dumps(provider_payload, ensure_ascii=False).encode("utf-8")
        )
        self.assertEqual(configuration_diagnostics()["status"], "configured")
        result = extract_intent("هدفون بی سیم تا سقف ۳ میلیون تومان", {"city": "tehran"})
        self.assertEqual(result["search_query"], "هدفون بی سیم")
        self.assertEqual(result["max_price_toman"], "3000000")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://ai.boxapi.ir/ai/v1/chat/completions")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(set(body), {"model", "messages"})
        self.assertEqual(body["model"], "gpt-5.4-mini")
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 15)

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="boxapi",
        LLM_API_KEY="test-secret",
        LLM_MODEL="gpt-5.4-mini",
        LLM_BASE_URL="https://attacker.example/ai/v1",
    )
    @patch("apps.agent.llm.urlopen")
    def test_boxapi_key_is_never_sent_to_unexpected_host(self, mocked_urlopen):
        from apps.agent.llm import configuration_diagnostics, extract_intent

        self.assertEqual(configuration_diagnostics()["status"], "invalid_base_url")
        self.assertIsNone(extract_intent("هدفون", {"city": "tehran"}))
        mocked_urlopen.assert_not_called()

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="boxapi",
        LLM_API_KEY="test-secret",
        LLM_MODEL="gpt-5.4-mini",
        LLM_BASE_URL="http://ai.boxapi.ir/ai/v1",
    )
    @patch("apps.agent.llm.urlopen")
    def test_boxapi_requires_https(self, mocked_urlopen):
        from apps.agent.llm import configuration_diagnostics, extract_intent

        self.assertEqual(configuration_diagnostics()["status"], "invalid_base_url")
        self.assertIsNone(extract_intent("هدفون", {"city": "tehran"}))
        mocked_urlopen.assert_not_called()

    @override_settings(LLM_ENABLED=True, LLM_PROVIDER="openai_compatible", LLM_API_KEY="", LLM_MODEL="")
    @patch("apps.agent.llm.urlopen")
    def test_unconfigured_adapter_returns_fallback_without_network(self, mocked_urlopen):
        from apps.agent.llm import extract_intent

        self.assertIsNone(extract_intent("هدفون بی‌سیم", {"city": "tehran"}))
        mocked_urlopen.assert_not_called()

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="openai_compatible",
        LLM_API_KEY="test-key",
        LLM_MODEL="test-model",
        LLM_BASE_URL="https://llm.example.test/v1",
        LLM_TIMEOUT_SECONDS=1,
    )
    @patch("apps.agent.llm.urlopen", side_effect=TimeoutError("simulated timeout"))
    def test_provider_timeout_falls_back_without_crashing(self, mocked_urlopen):
        from apps.agent.llm import extract_intent

        self.assertIsNone(extract_intent("هدفون بی‌سیم", {"city": "tehran"}))
        mocked_urlopen.assert_called_once()


class GenerativeUIComponentSchemaTests(SimpleTestCase):
    def test_vague_request_returns_a_clarification_form_not_a_fake_search(self):
        result = render_results_node({"search_query": "", "constraints": {"city": "tehran"}, "search_response": {"total": 0, "results": []}})
        self.assertEqual(result["ui_component"]["type"], "clarification_form")
        field_ids = [field["id"] for field in result["ui_component"]["data"]["fields"]]
        self.assertIn("product_query", field_ids)
        self.assertIn("max_price_toman", field_ids)
        self.assertIn("must_have_in_person_credit", field_ids)

    def test_empty_results_return_an_editable_constraint_form(self):
        result = render_results_node({
            "search_query": "هدفون",
            "constraints": {"city": "tehran", "max_price_toman": "1000000", "must_have_in_person_credit": True},
            "search_response": {"query": "هدفون", "total": 0, "results": []},
        })
        self.assertEqual(result["ui_component"]["type"], "empty_state")
        self.assertEqual(result["ui_component"]["data"]["fields"][0]["default_value"], "هدفون")
        credit_field = next(field for field in result["ui_component"]["data"]["fields"] if field["id"] == "must_have_in_person_credit")
        self.assertTrue(credit_field["default_value"])

    def test_ambiguous_catalog_hint_is_rendered_as_an_explicit_choice(self):
        result = render_results_node({
            "search_query": "فشارسنج",
            "constraints": {"city": "tehran"},
            "search_response": {
                "query": "فشارسنج", "total": 2, "results": [],
                "intent_hint": {
                    "label": "فشارسنج پزشکی",
                    "message": "حوزه پیش‌فرض پزشکی است.",
                    "alternative_label": "دیدن فشارسنج‌های صنعتی و محیطی",
                    "alternative_query": "فشارسنج صنعتی",
                },
            },
        })
        self.assertEqual(result["ui_component"]["type"], "component_stack")
        components = result["ui_component"]["data"]["components"]
        self.assertEqual(components[0]["type"], "category_choice")
        self.assertEqual(components[0]["data"]["alternative_query"], "فشارسنج صنعتی")
        self.assertEqual(components[1]["type"], "product_results")
