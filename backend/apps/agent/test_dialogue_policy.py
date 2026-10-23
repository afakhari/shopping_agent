"""Contract tests for pre-search intents and multi-turn clarification."""
from django.test import SimpleTestCase

from apps.agent.dialogue_policy import resolve_dialogue_policy


class DialoguePolicyContractTests(SimpleTestCase):
    def test_ambiguous_shorthand_asks_before_paid_search(self):
        for query in [
            "من یه لپ می خواهم مناسب مراسم عروسی",
            "لپ برای عروسی میخوام",
            "من لپ مناسب مراسم می خواهم",
        ]:
            with self.subTest(query=query):
                result = resolve_dialogue_policy(query, {"search_query": "هدفون"})
                self.assertEqual(result["kind"], "clarify")
                self.assertEqual(result["pending_dialogue"]["slot"], "product_kind")
                self.assertIn("لپ‌تاپ", result["reply"])

    def test_complete_laptop_wedding_request_still_clarifies_use_case(self):
        result = resolve_dialogue_policy("لپ تاپ مناسب مراسم عروسی می خواهم", {})
        self.assertEqual(result["kind"], "clarify")
        self.assertEqual(result["pending_dialogue"], {"slot": "laptop_usage"})

    def test_clarification_is_stateful_and_resumes_a_controlled_search(self):
        first = resolve_dialogue_policy("لپ برای عروسی تا ۳۰ میلیون می خواهم", {})
        self.assertEqual(first["pending_dialogue"]["budget"], "30000000")
        second = resolve_dialogue_policy("منظورم لپ تاپ است", {
            "pending_dialogue": first["pending_dialogue"],
        })
        self.assertEqual(second["pending_dialogue"]["slot"], "laptop_usage")
        third = resolve_dialogue_policy("برای پخش عکس و موسیقی", {
            "pending_dialogue": second["pending_dialogue"],
        })
        self.assertEqual(third["kind"], "search")
        self.assertEqual(third["query_override"], "لپ تاپ")
        self.assertEqual(third["constraint_updates"]["max_price_toman"], "30000000")

    def test_full_pending_dialogue_without_budget_asks_once_then_resumes(self):
        first = resolve_dialogue_policy("لپ تاپ برای عروسی می خوام", {})
        second = resolve_dialogue_policy("برای تدوین فیلم عروسی", {
            "pending_dialogue": first["pending_dialogue"],
        })
        self.assertEqual(second["kind"], "clarify")
        self.assertEqual(second["pending_dialogue"]["slot"], "laptop_budget")
        third = resolve_dialogue_policy("بودجه تا ۴۰ میلیون", {
            "pending_dialogue": second["pending_dialogue"],
        })
        self.assertEqual(third["kind"], "search")
        self.assertEqual(third["constraint_updates"]["max_price_toman"], "40000000")

    def test_technical_advice_never_turns_into_unrelated_product_search(self):
        queries = [
            "من دقیقا نمیدونم لپ تاپی که باید بخرم باید کارت گرافیک داشته باشه یا نه",
            "آیا لپ تاپ برای عروسی نیاز به کارت گرافیک مجزا دارد؟",
            "برای لپ تاپ کارت گرافیک مجزا؟",
            "لپ تاپ من رم بیشتری لازم دارد؟",
            "برای لپ تاپ چه پردازنده‌ای بهتره؟",
        ]
        for query in queries:
            with self.subTest(query=query):
                route = resolve_dialogue_policy(query, {"search_query": "لپ تاپ"})
                self.assertIn(route["kind"], {"clarify", "advice"})
                self.assertNotIn("query_override", route)

    def test_short_gpu_question_uses_focus_without_guessing_any_offer(self):
        route = resolve_dialogue_policy("کارت گرافیک لازم دارم؟", {"search_query": "لپ تاپ"})
        self.assertEqual(route["kind"], "advice")
        self.assertIn("گرافیک مجتمع", route["reply"])
        unknown = resolve_dialogue_policy("کارت گرافیک لازم دارم؟", {"search_query": "هدفون"})
        self.assertEqual(unknown["kind"], "clarify")

    def test_unrelated_product_discards_pending_laptop_goal(self):
        result = resolve_dialogue_policy(
            "هدفون می خوام",
            {"pending_dialogue": {"slot": "laptop_budget", "usage": "editing"}},
        )
        self.assertIsNone(result)

    def test_explicit_hardware_model_may_be_searched(self):
        result = resolve_dialogue_policy("لپ تاپ RTX 4060 معرفی کن", {})
        self.assertIsNone(result)

    def test_plain_laptop_search_is_not_swallowed_by_advice(self):
        for query in ("لپ تاپ", "لپ تاپ گیمینگ می خوام", "شارژر لپ تاپ"):
            with self.subTest(query=query):
                self.assertIsNone(resolve_dialogue_policy(query, {}))

    def test_not_every_word_containing_ram_is_a_memory_question(self):
        result = resolve_dialogue_policy("باید برم فروشگاه دوم؟", {})
        self.assertIsNone(result)

    def test_social_and_comparative_messages_remain_owned_by_existing_routes(self):
        for query in ("ممنون", "این دو تا چه فرقی دارند", "آدرس فروشگاه دوم"):
            with self.subTest(query=query):
                self.assertIsNone(resolve_dialogue_policy(query, {"search_query": "لپ تاپ"}))
