from decimal import Decimal
import json

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.catalog.models import Offer, Product, Shop
from apps.catalog.services.normalization import normalize_persian_text
from apps.missions.models import ContactAttempt, MissionEvent, PurchaseMission


@override_settings(DEMO_CONTACT_OUTCOMES="no_answer,confirmed_available,unavailable,closed,error", LLM_ENABLED=False)
class MissionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.shop_a = Shop.objects.create(
            source_id="shop_a",
            name="فروشگاه الف",
            address="تهران، خیابان نمونه، پاساژ نمونه، طبقه دوم، واحد ۱۲",
            lat=35.7001,
            lon=51.4001,
        )
        self.shop_b = Shop.objects.create(
            source_id="shop_b",
            name="فروشگاه ب",
            address="تهران، خیابان نمونه، طبقه اول، واحد ۳",
            lat=35.7010,
            lon=51.4010,
        )
        self.product = Product.objects.create(
            source_id="product_headphones",
            persian_title="هدفون بی‌سیم نمونه",
            normalized_title=normalize_persian_text("هدفون بی‌سیم نمونه"),
            category_name="هدفون",
            image_urls=[],
        )
        self.offer_a = Offer.objects.create(
            source_id="offer_a",
            product=self.product,
            shop=self.shop_a,
            price_toman=Decimal("750000"),
        )
        self.offer_b = Offer.objects.create(
            source_id="offer_b",
            product=self.product,
            shop=self.shop_b,
            price_toman=Decimal("800000"),
        )
        self.alternative_product = Product.objects.create(
            source_id="product_wired_headphones",
            persian_title="هدفون سیمی جایگزین",
            normalized_title=normalize_persian_text("هدفون سیمی جایگزین"),
            category_name="هدفون",
            image_urls=[],
        )
        self.alternative_offer = Offer.objects.create(
            source_id="offer_wired_alternative",
            product=self.alternative_product,
            shop=self.shop_b,
            price_toman=Decimal("500000"),
        )

    def _create_mission_and_search(self):
        create_response = self.client.post(
            "/api/v1/missions/",
            {
                "initial_message": "هدفون برای خرید حضوری",
                "constraints": {"max_price_toman": "1000000"},
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.content)
        mission_id = create_response.json()["mission_id"]
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/turns/",
            {"message": "یک هدفون بی‌سیم تا سقف ۱ میلیون تومان می‌خواهم"},
            format="json",
            HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(response.status_code, 200, getattr(response, "content", b""))
        self.assertTrue(response.streaming)
        self.assertTrue(response["Content-Type"].startswith("text/event-stream"))
        body = b"".join(response.streaming_content).decode("utf-8")
        events = [
            json.loads(line[6:])
            for line in body.splitlines()
            if line.startswith("data: ")
        ]
        self.assertTrue(any(event["type"] == "ui.component" for event in events))
        completed = next(event for event in events if event["type"] == "turn.completed")
        self.assertIn(completed["payload"].get("intent_parser"), {"heuristic", "llm"})
        self.assertIn(completed["payload"].get("agent_runtime"), {"langgraph", "deterministic_fallback"})
        return mission_id

    def test_create_mission_and_run_turn_emits_persisted_sse_events(self):
        mission_id = self._create_mission_and_search()
        mission = PurchaseMission.objects.get(pk=mission_id)
        self.assertEqual(mission.status, PurchaseMission.Status.WAITING_FOR_USER)
        self.assertIn(self.product.source_id, mission.state["candidate_product_ids"])
        stored_events = list(MissionEvent.objects.filter(mission=mission).order_by("seq"))
        self.assertGreaterEqual(len(stored_events), 6)
        self.assertEqual([event.seq for event in stored_events], list(range(1, len(stored_events) + 1)))

    def test_contact_outcome_is_server_controlled_and_failure_finds_alternative(self):
        mission_id = self._create_mission_and_search()
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_a.source_id, "offer_id": self.offer_a.source_id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["attempt"]["outcome"], "no_answer")
        self.assertEqual(body["attempt"]["source_type"], "demo_simulation")
        self.assertTrue(any(item["id"] == self.offer_b.source_id for item in body["alternatives"]))
        self.assertEqual(ContactAttempt.objects.count(), 1)

    def test_failed_contact_returns_eligible_substitute_products(self):
        mission_id = self._create_mission_and_search()
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_a.source_id, "offer_id": self.offer_a.source_id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        alternative_ids = [
            item["product"]["id"] for item in body["alternative_products"]
        ]
        self.assertIn(self.alternative_product.source_id, alternative_ids)
        mission = PurchaseMission.objects.get(pk=mission_id)
        self.assertIn(self.alternative_product.source_id, mission.state["candidate_product_ids"])

        # The substitute can immediately be selected for the next controlled availability check.
        follow_up = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_b.source_id, "offer_id": self.alternative_offer.source_id},
            format="json",
        )
        self.assertEqual(follow_up.status_code, 201, follow_up.content)

    def test_client_cannot_choose_simulated_contact_outcome(self):
        mission_id = self._create_mission_and_search()
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {
                "shop_id": self.shop_a.source_id,
                "offer_id": self.offer_a.source_id,
                "outcome": "confirmed_available",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactAttempt.objects.count(), 0)

    def test_contact_rejects_offer_outside_current_hard_constraints(self):
        mission_id = self._create_mission_and_search()
        self.offer_b.price_toman = Decimal("1500000")
        self.offer_b.save(update_fields=["price_toman"])
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_b.source_id, "offer_id": self.offer_b.source_id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactAttempt.objects.count(), 0)


    def test_no_answer_then_successful_alternative_is_reproducible(self):
        mission_id = self._create_mission_and_search()
        first = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_a.source_id, "offer_id": self.offer_a.source_id},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()["attempt"]["outcome"], "no_answer")
        second = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_b.source_id, "offer_id": self.offer_b.source_id},
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(second.json()["attempt"]["outcome"], "confirmed_available")
        visit_plan_events = [
            event for event in second.json()["events"]
            if event["type"] == "ui.component" and event["payload"].get("component") == "visit_plan"
        ]
        self.assertTrue(visit_plan_events)
        self.assertIn("شبیه‌سازی", visit_plan_events[0]["payload"]["data"]["source_label"])
        self.assertEqual(ContactAttempt.objects.count(), 2)

    def test_constraints_inferred_from_message_are_persisted_for_later_actions(self):
        create_response = self.client.post(
            "/api/v1/missions/",
            {"initial_message": "هدفون می‌خواهم", "constraints": {}},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201, create_response.content)
        mission_id = create_response.json()["mission_id"]
        turn = self.client.post(
            f"/api/v1/missions/{mission_id}/turns/",
            {"message": "یک هدفون تا سقف ۳ میلیون تومان، فقط خرید قسطی حضوری"},
            format="json",
        )
        self.assertEqual(turn.status_code, 200)
        mission = PurchaseMission.objects.get(pk=mission_id)
        self.assertEqual(mission.constraints["max_price_toman"], "3000000")
        self.assertTrue(mission.constraints["must_have_in_person_credit"])

    def test_contact_purpose_not_implemented_is_rejected(self):
        mission_id = self._create_mission_and_search()
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/contact-attempts/",
            {"shop_id": self.shop_a.source_id, "offer_id": self.offer_a.source_id, "purpose": "verify_price"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactAttempt.objects.count(), 0)

    def test_natural_language_credit_requirement_overrides_unchecked_ui_toggle(self):
        response = self.client.post(
            "/api/v1/missions/",
            {"initial_message": "هدفون می‌خواهم", "constraints": {"must_have_in_person_credit": False}},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        mission_id = response.json()["mission_id"]
        turn = self.client.post(
            f"/api/v1/missions/{mission_id}/turns/",
            {"message": "هدفون قسطی می‌خواهم"},
            format="json",
        )
        self.assertEqual(turn.status_code, 200)
        mission = PurchaseMission.objects.get(pk=mission_id)
        # No credit-enabled shop exists in this fixture, so the parser must safely yield no matches.
        self.assertTrue(mission.constraints["must_have_in_person_credit"])
        self.assertEqual(mission.state["candidate_product_ids"], [])

    def test_mission_snapshot_includes_sequenced_events(self):
        mission_id = self._create_mission_and_search()
        response = self.client.get(f"/api/v1/missions/{mission_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["mission_id"], mission_id)
        self.assertTrue(body["events"])
        self.assertEqual(body["events"][-1]["seq"], body["last_event_seq"])

    def test_mission_snapshot_returns_latest_bounded_event_window_in_order(self):
        mission_id = self._create_mission_and_search()
        from django.db import transaction
        from apps.missions.models import PurchaseMission
        from apps.missions.services import append_events_locked

        with transaction.atomic():
            mission = PurchaseMission.objects.select_for_update().get(pk=mission_id)
            append_events_locked(
                mission,
                [("test.marker", {"index": index}) for index in range(105)],
            )
        response = self.client.get(f"/api/v1/missions/{mission_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        events = response.json()["events"]
        self.assertEqual(len(events), 100)
        self.assertEqual(events, sorted(events, key=lambda item: item["seq"]))
        self.assertEqual(events[-1]["payload"]["index"], 104)

    def test_non_tehran_city_is_rejected_instead_of_returning_tehran_results(self):
        response = self.client.post(
            "/api/v1/missions/",
            {"initial_message": "کالا می‌خواهم", "constraints": {"city": "Berlin"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PurchaseMission.objects.count(), 0)

    def test_form_can_explicitly_clear_an_existing_budget(self):
        mission_id = self._create_mission_and_search()
        mission = PurchaseMission.objects.get(pk=mission_id)
        mission.constraints = {**mission.constraints, "max_price_toman": "1000000"}
        mission.save(update_fields=["constraints"])
        response = self.client.post(
            f"/api/v1/missions/{mission_id}/turns/",
            {"message": "هدفون", "constraints": {"max_price_toman": None}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        mission.refresh_from_db()
        self.assertIsNone(mission.constraints.get("max_price_toman"))
