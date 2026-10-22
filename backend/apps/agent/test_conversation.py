from unittest.mock import patch

from django.test import SimpleTestCase
from apps.agent.conversation import classify_conversation_intent
from apps.agent.graph import _query_from_message, parse_request_node, search_catalog_node


class ConversationGuardTests(SimpleTestCase):
    def test_greetings_do_not_leak_to_product_query(self):
        for phrase in [
            "احوال شما؟", "احوالِ شما؟؟", "احوالتون چطوره؟",
            "سلام، حال شما چطوره؟", "حالِ شما چطور است؟", "حال شما خوبه؟",
            "احوال شما امروز چطوره؟", "چطوری؟", "مرسی", "خداحافظ!",
            "چطور ازت استفاده کنم؟",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIsNotNone(classify_conversation_intent(phrase))
                self.assertEqual(_query_from_message(phrase), "")

    def test_commercial_message_cannot_be_swallowed_by_social_router(self):
        for phrase in [
            "سلام، هدفون تا سه میلیون می‌خواهم",
            "احوال شما، یک هدفون معرفی کن",
            "چه خبر از قیمت لپ‌تاپ‌های گیمینگ؟",
            "چطور هدفون مناسب بخرم؟",
            "خرید اعتباری حضوری",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIsNone(classify_conversation_intent(phrase))

    @patch("apps.agent.graph.extract_intent")
    def test_graph_parser_does_not_call_model_for_social_phrase(self, mocked_extract):
        state = parse_request_node({
            "user_message": "احوال شما؟",
            "constraints": {"city": "tehran", "must_have_in_person_credit": True},
        })
        self.assertEqual(state["search_query"], "")
        self.assertTrue(state["constraints"]["must_have_in_person_credit"])
        mocked_extract.assert_not_called()

    @patch("apps.agent.graph.product_search_page")
    def test_empty_product_query_cannot_return_random_catalogue(self, mocked_search):
        result = search_catalog_node({
            "search_query": "",
            "constraints": {"city": "tehran"},
            "search_filters": {},
        })
        self.assertEqual(result["search_response"]["total"], 0)
        mocked_search.assert_not_called()
