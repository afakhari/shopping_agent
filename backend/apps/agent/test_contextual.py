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
    def test_wedding_lap_ambiguity_never_guesses_a_product(self):
        state = {"search_query": "هدفون", "visible_product_ids": ["p1"]}
        for utterance in (
            "من یه لپ می خواهم مناسب مراسم عروسی",
            "یه لپ برای عروسی میخوام",
            "لپ می خواهم",
        ):
            with self.subTest(utterance=utterance):
                result = classify_contextual_turn(utterance, state)
                self.assertEqual(result["kind"], "clarify")
                self.assertIn("لپ‌تاپ", result["reply"])
                self.assertIn("آرایش", result["reply"])
        self.assertEqual(
            classify_contextual_turn("یه لپ تاپ برای تدوین عروسی میخوام", state)["kind"],
            "search",
        )

    def test_laptop_gpu_question_gives_grounded_advice_not_catalog_search(self):
        state = {"search_query": "لپ تاپ", "candidate_product_ids": ["p1"]}
        for utterance in (
            "من دقیقا نمیدونم لپ تاپی که باید بخرم باید کارت گرافیک داشته باشه یا نه",
            "آیا لپ تاپ برای مراسم عروسی نیاز به کارت گرافیک مجزا داره؟",
        ):
            with self.subTest(utterance=utterance):
                result = classify_contextual_turn(utterance, state)
                self.assertEqual(result["kind"], "clarify")
                self.assertIn("گرافیک مجتمع", result["reply"])
                self.assertIn("تدوین", result["reply"])
        self.assertEqual(
            classify_contextual_turn("لپ تاپ با کارت گرافیک RTX 4060 میخوام", state)["kind"],
            "search",
        )

    def test_budget_change_reuses_catalogue_query(self):
        decision = classify_contextual_turn("بودجه‌م شد ۲ میلیون", {"search_query": "هدفون"})
        self.assertEqual(decision["kind"], "refine")
        self.assertEqual(decision["query"], "هدفون")
        self.assertEqual(decision["constraint_updates"]["max_price_toman"], "2000000")

    def test_budget_grouped_thousands_refines_to_actual_toman(self):
        decision = classify_contextual_turn("بودجه م شد ۳٬۰۰۰٬۰۰۰ تومان", {"search_query": "هدفون"})
        self.assertEqual(decision["kind"], "refine")
        self.assertEqual(decision["constraint_updates"]["max_price_toman"], "3000000")

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

    def test_contact_inquiry_requires_explicit_consent(self):
        state = {"search_query": "هدفون", "selected_offer_id": "o1"}
        self.assertEqual(classify_contextual_turn("موجودی رو بررسی کن", state), {
            "kind": "contact_prompt", "offer_id": "o1",
        })
        self.assertEqual(classify_contextual_turn("موجودی رو بررسی کن", {
            "search_query": "هدفون",
        })["kind"], "clarify")

    def test_compare_uses_persisted_selection_not_guessed_models(self):
        context = {"search_query": "هدفون", "compared_product_ids": ["p1", "p2"]}
        self.assertEqual(classify_contextual_turn("این دو تا چه فرقی دارند", context)["kind"], "compare")
        self.assertEqual(classify_contextual_turn("این دو تا چه فرقی دارند", {
            "search_query": "هدفون",
        })["kind"], "clarify")

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

    def test_future_seller_hours_are_not_misreported_as_current_open_status(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        mission.state = {**mission.state, "active_surface": "sellers",
                         "visible_offer_ids": ["context_offer_0"],
                         "selected_product_id": self.first.source_id,
                         "selected_offer_id": "context_offer_0"}
        mission.save(update_fields=["state"])
        events = self.turn("فروشنده اول فردا صبح بازه؟")
        reply = next(event["payload"]["text"] for event in events if event["type"] == "assistant.message")
        self.assertIn("برنامه هفتگی ثبت‌شده", reply)
        self.assertNotIn("طبق برنامه ثبت‌شده باز است", reply)

    def test_turn_request_id_replays_without_duplicate_events(self):
        payload = {"message": "هدفون", "client_request_id": "turn-idempotent-001"}
        url = f"/api/v1/missions/{self.mission_id}/turns/"
        first = self.client.post(url, payload, format="json", HTTP_ACCEPT="text/event-stream")
        self.assertEqual(first.status_code, 200)
        saved_payload = b"".join(first.streaming_content)
        count = PurchaseMission.objects.get(pk=self.mission_id).events.count()
        repeated = self.client.post(url, payload, format="json", HTTP_ACCEPT="text/event-stream")
        self.assertEqual(repeated.status_code, 200)
        def decoded_events(raw):
            return [json.loads(line[6:]) for line in raw.decode("utf-8").splitlines()
                    if line.startswith("data: ")]
        self.assertEqual(decoded_events(b"".join(repeated.streaming_content)),
                         decoded_events(saved_payload))
        self.assertEqual(PurchaseMission.objects.get(pk=self.mission_id).events.count(), count)
        changed = self.client.post(url, {
            "message": "دوربین", "client_request_id": "turn-idempotent-001",
        }, format="json", HTTP_ACCEPT="text/event-stream")
        self.assertEqual(changed.status_code, 400)

    def test_paired_null_coordinates_clear_existing_geofence(self):
        created = self.client.post("/api/v1/missions/", {
            "initial_message": "هدفون",
            "constraints": {"lat": 35.7, "lon": 51.4, "radius_m": 3000,
                            "sort": "distance_asc"},
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.mission_id = created.json()["mission_id"]
        self.turn("هدفون")
        response = self.client.post(
            f"/api/v1/missions/{self.mission_id}/turns/",
            {"message": "هدفون", "constraints": {
                "lat": None, "lon": None, "radius_m": None, "sort": "relevance",
            }}, format="json", HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(response.status_code, 200)
        list(response.streaming_content)
        saved = PurchaseMission.objects.get(pk=self.mission_id).constraints
        self.assertNotIn("lat", saved)
        self.assertNotIn("lon", saved)
        self.assertNotIn("radius_m", saved)

    def test_focus_change_invalidates_previous_visit_plan(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        mission.state = {**mission.state, "visit_plan": {"offer_id": "old_offer"}}
        mission.save(update_fields=["state"])
        response = self.client.post(f"/api/v1/missions/{self.mission_id}/focus/", {
            "action": "select_product", "result_set_id": mission.state["result_set_id"],
            "product_id": self.first.source_id,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("visit_plan", response.json()["state"])
        self.assertEqual(self.client.get(
            f"/api/v1/missions/{self.mission_id}/visit-plan/").status_code, 404)

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

    def test_wedding_lap_and_gpu_advice_preserve_results_and_skip_paid_model(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        original_state = mission.state.copy()
        prompts = (
            ("من یه لپ می خواهم مناسب مراسم عروسی", "لپ‌تاپ"),
            ("من دقیقا نمیدونم لپ تاپی که باید بخرم باید کارت گرافیک داشته باشه یا نه",
             "گرافیک مجتمع"),
        )
        with patch("apps.missions.views.extract_intent") as model, patch(
            "apps.missions.views.run_purchase_graph"
        ) as graph:
            for message, expected in prompts:
                events = self.turn(message)
                self.assertEqual([e["type"] for e in events], [
                    "user.message", "assistant.message", "turn.completed",
                ])
                self.assertIn(expected, events[1]["payload"]["text"])
                self.assertEqual(events[-1]["payload"]["intent_parser"], "contextual")
            model.assert_not_called()
            graph.assert_not_called()
        mission.refresh_from_db()
        self.assertEqual(mission.state, original_state)
        self.assertEqual(mission.constraints["max_price_toman"], "1000000")

    def test_ambiguous_wedding_query_before_any_search_asks_without_catalog(self):
        created = self.client.post(
            "/api/v1/missions/",
            {"initial_message": "من یه لپ می خواهم مناسب مراسم عروسی"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.mission_id = created.json()["mission_id"]
        with patch("apps.missions.views.extract_intent") as model, patch(
            "apps.missions.views.run_purchase_graph"
        ) as graph:
            events = self.turn("من یه لپ می خواهم مناسب مراسم عروسی")
            model.assert_not_called()
            graph.assert_not_called()
        self.assertIn("آرایش", events[1]["payload"]["text"])
        self.assertNotIn("ui.component", [e["type"] for e in events])
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        self.assertFalse((mission.state or {}).get("candidate_product_ids"))

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

    def test_sellers_for_explicitly_selected_product_outside_ordinal_cards(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        product_id = mission.state["candidate_product_ids"][0]
        mission.state = {
            **mission.state, "selected_product_id": product_id,
            "visible_product_ids": [],
        }
        mission.save(update_fields=["state"])
        events = self.turn("فروشنده ها")
        cards = [e["payload"] for e in events if e["type"] == "ui.component"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["component"], "seller_options")
        self.assertTrue(cards[0]["data"]["offers"])
        self.assertEqual(cards[0]["data"]["product_id"], product_id)

    def test_chat_contact_consent_does_not_run_simulator_or_search(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        product_id = mission.state["visible_product_ids"][0]
        offer = Offer.objects.filter(product_id=product_id).first()
        token = mission.state["result_set_id"]
        endpoint = f"/api/v1/missions/{self.mission_id}/focus/"
        focused = self.client.post(endpoint, {
            "action": "view_sellers", "result_set_id": token, "product_id": product_id,
            "offer_ids": [offer.source_id],
        }, format="json")
        self.assertEqual(focused.status_code, 200)
        selected = self.client.post(endpoint, {
            "action": "select_offer", "result_set_id": token,
            "offer_id": offer.source_id,
        }, format="json")
        self.assertEqual(selected.status_code, 200)
        with patch("apps.missions.views.simulate_contact") as simulate, patch(
            "apps.missions.views.run_purchase_graph"
        ) as graph:
            events = self.turn("موجودی رو بررسی کن")
            simulate.assert_not_called()
            graph.assert_not_called()
        prompts = [e["payload"] for e in events if e["type"] == "ui.component"]
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["component"], "contact_prompt")
        self.assertEqual(prompts[0]["data"]["offer_id"], offer.source_id)
        self.assertEqual(prompts[0]["data"]["source_type"], "demo_simulation")

    def test_compare_from_confirmed_offer_data_and_restore_snapshot(self):
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        ids = mission.state["visible_product_ids"][:2]
        self.assertEqual(len(ids), 2)
        self.first.specs = [{"key": "رنگ", "value": "مشکی"}]
        self.second.specs = [{"key": "رنگ", "value": "سفید"}]
        self.first.save(update_fields=["specs"])
        self.second.save(update_fields=["specs"])
        focus = self.client.post(
            f"/api/v1/missions/{self.mission_id}/focus/",
            {"action": "set_compare", "product_ids": ids,
             "result_set_id": mission.state["result_set_id"]}, format="json",
        )
        self.assertEqual(focus.status_code, 200, focus.content)
        with patch("apps.missions.views.run_purchase_graph") as graph:
            events = self.turn("این دو تا چه فرقی دارند")
            graph.assert_not_called()
        components = [e["payload"] for e in events if e["type"] == "ui.component"]
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0]["component"], "comparison_table")
        self.assertEqual(len(components[0]["data"]["rows"]), 2)
        self.assertEqual(components[0]["data"]["availability_verified"], False)
        snapshot = self.client.get(f"/api/v1/missions/{self.mission_id}/")
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot.json()["state"]["compared_product_ids"], ids)
        old = self.client.post(
            f"/api/v1/missions/{self.mission_id}/focus/",
            {"action": "set_compare", "product_ids": ids,
             "result_set_id": "not-current"}, format="json",
        )
        self.assertEqual(old.status_code, 400)

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
        repeated = self.client.post(endpoint, {
            "action": "select_product", "product_id": first_id,
            "result_set_id": result_set_id,
        }, format="json")
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()["events"], [])
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
        location_components = [e["payload"] for e in events if e["type"] == "ui.component"]
        self.assertEqual(len(location_components), 1)
        self.assertEqual(location_components[0]["component"], "location_choice")
        self.assertEqual(location_components[0]["data"]["city"], "tehran")

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
