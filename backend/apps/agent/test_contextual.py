"""Contextual routing regression tests: every short turn keeps the shopping mission."""
from decimal import Decimal
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.agent.contextual import classify_contextual_turn
from apps.catalog.models import Offer, Product, Shop
from apps.catalog.services.normalization import normalize_persian_text
from apps.missions.models import PurchaseMission


class ContextualRouterTests(TestCase):
    def test_budget_change_reuses_catalogue_query(self):
        decision = classify_contextual_turn("بودجه‌م شد ۲ میلیون", {"search_query": "هدفون"})
        self.assertEqual(decision["kind"], "refine")
        self.assertEqual(decision["query"], "هدفون")
        self.assertEqual(decision["constraint_updates"]["max_price_toman"], "2000000")

    def test_credit_is_an_offer_filter_not_a_new_product(self):
        decision = classify_contextual_turn("فقط قسطی", {"search_query": "هدفون"})
        self.assertEqual(decision["kind"], "refine")
        self.assertTrue(decision["constraint_updates"]["must_have_in_person_credit"])

    def test_unambiguous_product_ordinal(self):
        context = {"visible_product_ids": ["p1", "p2"], "search_query": "هدفون"}
        self.assertEqual(classify_contextual_turn("مدل دوم رو انتخاب کن", context)["product_id"], "p2")
        self.assertEqual(classify_contextual_turn("دومی", context)["product_id"], "p2")

    def test_unseen_or_seller_reference_must_clarify(self):
        context = {"visible_product_ids": ["p1"], "search_query": "هدفون"}
        self.assertEqual(classify_contextual_turn("سومی", context)["kind"], "clarify")
        self.assertEqual(classify_contextual_turn("فروشگاه دوم", context)["kind"], "clarify")

    def test_normal_shopping_request_preserves_catalogue_path(self):
        self.assertEqual(classify_contextual_turn("هدفون تا ۳ میلیون", {"search_query": "لپ تاپ"})["kind"], "search")
        self.assertEqual(classify_contextual_turn("هدفون می خوام", {})["kind"], "search")

    def test_why_does_not_start_unrelated_search(self):
        self.assertEqual(classify_contextual_turn("چرا اینو پیشنهاد دادی", {"search_query": "هدفون"})["kind"], "explain")


@override_settings(LLM_ENABLED=False)
class ContextualMissionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        shop = Shop.objects.create(source_id="context_shop", name="فروشگاه نمونه")
        self.first = Product.objects.create(
            source_id="context_first", persian_title="هدفون بی سیم اول",
            normalized_title=normalize_persian_text("هدفون بی سیم اول"), category_name="هدفون",
            image_urls=[],
        )
        self.second = Product.objects.create(
            source_id="context_second", persian_title="هدفون بی سیم دوم",
            normalized_title=normalize_persian_text("هدفون بی سیم دوم"), category_name="هدفون",
            image_urls=[],
        )
        for ix, product in enumerate((self.first, self.second)):
            Offer.objects.create(
                source_id=f"context_offer_{ix}", product=product, shop=shop,
                price_toman=Decimal("700000") + Decimal(ix * 100000),
            )
        created = self.client.post(
            "/api/v1/missions/",
            {"initial_message": "هدفون", "constraints": {"max_price_toman": "1000000"}}, format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.mission_id = created.json()["mission_id"]
        self.turn("هدفون")

    def turn(self, message):
        response = self.client.post(
            f"/api/v1/missions/{self.mission_id}/turns/",
            {"message": message}, format="json", HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(response.status_code, 200, getattr(response, "content", b""))
        return [json.loads(row[6:]) for row in b"".join(response.streaming_content).decode("utf-8").splitlines() if row.startswith("data: ")]

    def test_product_reference_keeps_previous_results_and_does_not_search(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        visible = mission.state["visible_product_ids"]
        self.assertGreaterEqual(len(visible), 2)
        with patch("apps.missions.views.extract_intent") as model, patch(
            "apps.missions.views.run_purchase_graph"
        ) as graph:
            events = self.turn("مدل دوم رو انتخاب کن")
            graph.assert_not_called()
            model.assert_not_called()
        self.assertEqual([x["type"] for x in events], ["user.message", "assistant.message", "turn.completed"])
        mission.refresh_from_db()
        self.assertEqual(mission.state["selected_product_id"], visible[1])
        self.assertEqual(mission.state["visible_product_ids"], visible)
        self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")

    def test_budget_only_followup_preserves_query_and_limits_offers(self):
        events = self.turn("بودجه‌م شد ۵۰۰ هزار")
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        self.assertEqual(mission.constraints["max_price_toman"], "500000")
        self.assertEqual(mission.state["search_query"], "هدفون")
        self.assertEqual(mission.state["candidate_product_ids"], [])
        self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")

    def test_ambiguous_reference_never_runs_catalogue(self):
        with patch("apps.missions.views.run_purchase_graph") as graph:
            events = self.turn("فروشگاه دوم")
            graph.assert_not_called()
        self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")
        self.assertNotIn("ui.component", [x["type"] for x in events])
