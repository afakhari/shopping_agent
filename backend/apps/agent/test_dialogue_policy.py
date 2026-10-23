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

    def test_video_editing_recommendation_is_saved_until_budget_answer(self):
        first = resolve_dialogue_policy(
            "چه لپ تاپی برای تدوین ویدیو مناسب من هست؟", {}
        )
        self.assertEqual(first["kind"], "clarify")
        self.assertEqual(first["pending_dialogue"]["slot"], "recommendation_budget")
        self.assertEqual(first["pending_dialogue"]["family"], "laptop")
        self.assertEqual(first["pending_dialogue"]["usage"], "video_editing")
        continued = resolve_dialogue_policy(
            "تدوین ویدیوی سبک و قیمت تا سقف 200 میلیون",
            {"pending_dialogue": first["pending_dialogue"]},
        )
        self.assertEqual(continued["kind"], "search")
        self.assertEqual(continued["query_override"], "لپ تاپ")
        self.assertEqual(continued["usage_profile"], "video_editing")
        self.assertEqual(
            continued["constraint_updates"]["max_price_toman"], "200000000"
        )

    def test_single_message_video_editing_with_budget_keeps_product_family(self):
        result = resolve_dialogue_policy(
            "لپ تاپ مناسب تدوین ویدیو تا ۲۰۰ میلیون میخوام", {}
        )
        self.assertEqual(result["query_override"], "لپ تاپ")
        self.assertEqual(result["usage_profile"], "video_editing")
        self.assertEqual(result["constraint_updates"]["max_price_toman"], "200000000")

    def test_unrelated_video_editing_without_laptop_stays_unresolved(self):
        result = resolve_dialogue_policy(
            "تدوین ویدیوی سبک و قیمت تا سقف 200 میلیون", {}
        )
        self.assertIsNone(result)

    def test_generalized_recommendation_slots_for_families(self):
        from apps.agent.recommendation_frame import resolve_recommendation_frame
        cases = [
            ("چه گوشی برای عکاسی مناسب است؟", "۳۰ میلیون", "گوشی", "phone", "photography"),
            ("چه هدفونی برای درس مناسب است؟", "تا ۲ میلیون", "هدفون", "headphones", "study"),
            ("چه تبلتی برای درس مناسب است؟", "بودجه ۵ میلیون", "تبلت", "tablet", "study"),
            ("کدام تلویزیون برای گیم مناسب است؟", "تا ۳۰ میلیون", "تلویزیون", "television", "gaming"),
            ("چه لپ تاپی برای تدوین مناسب است؟", "200 میلیون", "لپ تاپ", "laptop", "video_editing"),
        ]
        for initial, followup, canonical, family, usage in cases:
            with self.subTest(initial=initial):
                first = resolve_recommendation_frame(initial, {})
                self.assertEqual(first["kind"], "clarify")
                self.assertEqual(first["pending_dialogue"]["family"], family)
                self.assertEqual(first["pending_dialogue"]["usage"], usage)
                final = resolve_recommendation_frame(followup, {
                    "pending_dialogue": first["pending_dialogue"],
                })
                self.assertEqual(final["kind"], "search")
                self.assertEqual(final["query_override"], canonical)
                self.assertEqual(final["shopping_need"]["family"], family)
                self.assertEqual(final["usage_profile"], usage)

    def test_missing_usage_then_budget_answer_does_not_guess_use_case(self):
        from apps.agent.recommendation_frame import resolve_recommendation_frame
        first = resolve_recommendation_frame("چه لپ تاپی بخرم؟", {})
        self.assertEqual(first["pending_dialogue"]["slot"], "recommendation_usage")
        second = resolve_recommendation_frame("تا ۲۰۰ میلیون", {
            "pending_dialogue": first["pending_dialogue"],
        })
        self.assertEqual(second["kind"], "clarify")
        self.assertEqual(second["pending_dialogue"]["budget"], "200000000")
        third = resolve_recommendation_frame("تدوین ویدیو سبک", {
            "pending_dialogue": second["pending_dialogue"],
        })
        self.assertEqual(third["query_override"], "لپ تاپ")
        self.assertEqual(third["shopping_need"]["intensity"], "light")

    def test_interruptions_do_not_turn_into_unrelated_implicit_searches(self):
        from apps.agent.recommendation_frame import resolve_recommendation_frame
        old = {"slot": "recommendation_budget", "family": "laptop",
               "usage": "video_editing", "intensity": "light"}
        state = {"pending_dialogue": old}
        self.assertIsNone(resolve_recommendation_frame("گوشی میخوام", state))
        self.assertIsNone(resolve_recommendation_frame("چه پردازنده ای لازمه؟", state))
        cancelled = resolve_recommendation_frame("بی خیال", state)
        self.assertEqual(cancelled["kind"], "clarify")
        self.assertIsNone(cancelled["pending_dialogue"])
        self.assertIsNone(resolve_recommendation_frame("کیف لپ تاپ ارزان", {}))

    def test_recommendation_uses_canonical_query_and_not_user_usecase_words(self):
        first = resolve_dialogue_policy("چه لپ تاپی مناسب تدوین ویدیوی سبک است؟", {})
        self.assertEqual(first["pending_dialogue"]["family"], "laptop")
        second = resolve_dialogue_policy(
            "تدوین ویدیوی سبک و قیمت تا سقف 200 میلیون",
            {"pending_dialogue": first["pending_dialogue"]},
        )
        self.assertEqual(second["query_override"], "لپ تاپ")
        self.assertEqual(second["constraint_updates"]["max_price_toman"], "200000000")

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

    def test_unrelated_verb_is_not_mistaken_for_laptop_memory(self):
        result = resolve_dialogue_policy("باید برم فروشگاه دوم؟", {})
        self.assertEqual(result["kind"], "clarify")
        self.assertNotIn("گرافیک", result["reply"])
        self.assertNotIn("رم", result["reply"])

    def test_unseen_product_advice_question_does_not_reach_search(self):
        for query in (
            "آیا هدفون نویز کنسلینگ لازم دارم؟",
            "چطور یک دوربین مناسب عروسی انتخاب کنم؟",
            "برای خرید گوشی چه ویژگی هایی مهمه؟",
            "نویز کنسلینگ چیه؟",
            "کدوم هدفون رو بخرم؟",
        ):
            with self.subTest(query=query):
                decision = resolve_dialogue_policy(query, {"search_query": "هدفون"})
                self.assertEqual(decision["kind"], "clarify")

    def test_social_and_comparative_messages_remain_owned_by_existing_routes(self):
        for query in ("ممنون", "این دو تا چه فرقی دارند", "آدرس فروشگاه دوم"):
            with self.subTest(query=query):
                self.assertIsNone(resolve_dialogue_policy(query, {"search_query": "لپ تاپ"}))
