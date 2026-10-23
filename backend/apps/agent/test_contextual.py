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
        self.assertEqual(classify_contextual_turn("دومی رو بیشتر دوست دارم", context)["product_id"], "p2")
        combined = classify_contextual_turn("دومی خوبه ولی نزدیکتر پیدا کن", context)
        self.assertEqual(combined["kind"], "select_product")
        self.assertTrue(combined["prefer_distance"])

    def test_unseen_or_seller_reference_must_clarify(self):
        context = {"visible_product_ids": ["p1"], "search_query": "هدفون"}
        self.assertEqual(classify_contextual_turn("سومی", context)["kind"], "clarify")
        self.assertEqual(classify_contextual_turn("فروشگاه دوم", context)["kind"], "clarify")

    def test_normal_shopping_request_preserves_catalogue_path(self):
        self.assertEqual(classify_contextual_turn("هدفون تا ۳ میلیون", {"search_query": "لپ تاپ"})["kind"], "search")
        self.assertEqual(classify_contextual_turn("هدفون می خوام", {})["kind"], "search")

    def test_changing_product_and_budget_is_not_a_budget_only_turn(self):
        self.assertEqual(classify_contextual_turn(
            "تا ۴ میلیون گوشی می خوام", {"search_query": "لپ تاپ"}
        )["kind"], "search")
        self.assertEqual(classify_contextual_turn(
            "فقط قسطی گوشی می خوام", {"search_query": "لپ تاپ"}
        )["kind"], "search")

    def test_seller_focus_changes_ordinal_referent(self):
        state = {
            "search_query": "هدفون", "active_surface": "sellers",
            "visible_product_ids": ["p1", "p2"],
            "visible_offer_ids": ["o1", "o2"],
        }
        self.assertEqual(classify_contextual_turn("دومی", state)["offer_id"], "o2")
        self.assertEqual(classify_contextual_turn("فروشگاه دوم", state)["offer_id"], "o2")
        self.assertEqual(classify_contextual_turn("آدرس فروشگاه دوم", state)["kind"], "seller_details")

    def test_seller_unavailability_does_not_become_product_search(self):
        state = {"search_query": "هدفون", "selected_offer_id": "offer1"}
        self.assertEqual(classify_contextual_turn("فروشنده جواب نداد", state), {
            "kind": "seller_recovery", "offer_id": "offer1",
        })

    def test_two_stage_request_preserves_product_and_seller_intent(self):
        state = {"search_query": "هدفون", "visible_product_ids": ["p1", "p2"],
                 "active_surface": "products"}
        result = classify_contextual_turn("دومی خوبه ولی فروشنده نزدیک تر پیدا کن", state)
        self.assertEqual(result["kind"], "select_product")
        self.assertEqual(result["product_id"], "p2")
        self.assertTrue(result["explore_sellers"])

    def test_why_does_not_start_unrelated_search(self):
        self.assertEqual(classify_contextual_turn("چرا اینو پیشنهاد دادی", {"search_query": "هدفون"})["kind"], "explain")

    def test_filters_before_product_are_remembered(self):
        decision = classify_contextual_turn("بودجه‌م شد ۳ میلیون", {})
        self.assertEqual(decision["kind"], "clarify")
        self.assertEqual(decision["pending_constraints"]["max_price_toman"], "3000000")


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

    def test_explicit_brand_model_are_true_hard_offer_filters(self):
        self.first.brand_name = "برند الف"
        self.first.model = "A1"
        self.first.save(update_fields=["brand_name", "model"])
        self.second.brand_name = "برند ب"
        self.second.model = "B2"
        self.second.save(update_fields=["brand_name", "model"])
        created = self.client.post("/api/v1/missions/", {
            "initial_message": "هدفون",
            "constraints": {"brand_name": "برند الف", "model_exact": "A1"},
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.mission_id = created.json()["mission_id"]
        self.turn("هدفون")
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        self.assertEqual(mission.state["candidate_product_ids"], [self.first.source_id])
        filters = mission.constraints
        self.assertEqual(filters["brand_name"], "برند الف")
        self.assertEqual(filters["model_exact"], "A1")

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

    def test_structured_focus_action_and_stale_result_guard(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        result_set_id = mission.state["result_set_id"]
        first_id = mission.state["visible_product_ids"][0]
        endpoint = f"/api/v1/missions/{self.mission_id}/focus/"
        selected = self.client.post(endpoint, {
            "action": "select_product", "product_id": first_id,
            "result_set_id": result_set_id,
        }, format="json")
        self.assertEqual(selected.status_code, 200, selected.content)
        self.assertEqual(selected.json()["state"]["selected_product_id"], first_id)
        matching = Offer.objects.filter(product_id=first_id).first()
        self.assertIsNotNone(matching)
        focused = self.client.post(endpoint, {
            "action": "view_sellers", "product_id": first_id,
            "offer_ids": [matching.source_id], "result_set_id": result_set_id,
        }, format="json")
        self.assertEqual(focused.status_code, 200, focused.content)
        self.assertEqual(focused.json()["state"]["active_surface"], "sellers")
        chosen = self.client.post(endpoint, {
            "action": "select_offer", "offer_id": matching.source_id,
            "result_set_id": result_set_id,
        }, format="json")
        self.assertEqual(chosen.status_code, 200, chosen.content)
        self.assertEqual(chosen.json()["state"]["selected_offer_id"], matching.source_id)
        old = self.client.post(endpoint, {
            "action": "select_product", "product_id": first_id,
            "result_set_id": "no-longer-current",
        }, format="json")
        self.assertEqual(old.status_code, 400)

    def test_contextual_filter_change_marks_old_surface_stale(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        before = mission.state["result_set_id"]
        response = self.client.post(
            f"/api/v1/missions/{self.mission_id}/turns/",
            {"message": "مدل دوم رو انتخاب کن",
             "constraints": {"max_price_toman": "500000"}},
            format="json", HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(response.status_code, 200)
        mission.refresh_from_db()
        self.assertEqual(mission.constraints["max_price_toman"], "500000")
        self.assertTrue(mission.state["results_stale"])
        self.assertIsNone(mission.state.get("selected_product_id"))
        rejected = self.client.post(
            f"/api/v1/missions/{self.mission_id}/focus/",
            {"action": "select_product", "product_id": self.first.source_id,
             "result_set_id": before}, format="json",
        )
        self.assertEqual(rejected.status_code, 400)

    def test_reported_seller_failure_shows_grounded_backup_without_contact(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        current_product = mission.state["visible_product_ids"][0]
        original = Offer.objects.filter(product_id=current_product).first()
        self.assertIsNotNone(original)
        second_shop = Shop.objects.create(
            source_id="context_backup_shop", name="فروشگاه پشتیبان",
        )
        backup = Offer.objects.create(
            source_id="context_backup_offer", shop=second_shop,
            product_id=current_product, price_toman=Decimal("820000"),
        )
        endpoint = f"/api/v1/missions/{self.mission_id}/focus/"
        token = mission.state["result_set_id"]
        self.client.post(endpoint, {
            "action": "view_sellers", "product_id": current_product,
            "result_set_id": token, "offer_ids": [original.source_id, backup.source_id],
        }, format="json")
        chosen = self.client.post(endpoint, {
            "action": "select_offer", "offer_id": original.source_id,
            "result_set_id": token,
        }, format="json")
        self.assertEqual(chosen.status_code, 200, chosen.content)
        with patch("apps.missions.views.simulate_contact") as contact:
            events = self.turn("فروشنده جواب نداد")
            contact.assert_not_called()
        cards = [entry["payload"] for entry in events if entry["type"] == "ui.component"]
        self.assertTrue(cards)
        self.assertEqual(cards[0]["component"], "seller_options")
        self.assertEqual(cards[0]["data"]["offers"][0]["id"], backup.source_id)
        self.assertIn("طبق گزارشی که دادی", events[1]["payload"]["text"])

    def test_ambiguous_reference_never_runs_catalogue(self):
        with patch("apps.missions.views.run_purchase_graph") as graph:
            events = self.turn("فروشگاه دوم")
            graph.assert_not_called()
        self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")
        self.assertNotIn("ui.component", [x["type"] for x in events])

    def test_nearest_without_location_asks_not_bad_request(self):
        events = self.turn("نزدیک ترین")
        self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")
        self.assertIn("محدوده", events[1]["payload"]["text"])

    def test_credit_followup_keeps_prior_product_query(self):
        self.turn("فقط قسطی")
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        self.assertTrue(mission.constraints["must_have_in_person_credit"])
        self.assertEqual(mission.state["search_query"], "هدفون")

    def test_pre_product_budget_remains_for_next_search(self):
        new = self.client.post(
            "/api/v1/missions/",
            {"initial_message": "بودجه سه میلیون", "constraints": {}}, format="json",
        )
        self.mission_id = new.json()["mission_id"]
        events = self.turn("بودجه‌م شد ۳ میلیون")
        self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        self.assertEqual(mission.constraints["max_price_toman"], "3000000")
        self.turn("هدفون")
        mission.refresh_from_db()
        self.assertEqual(mission.constraints["max_price_toman"], "3000000")
