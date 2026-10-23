"""No paid Neshan requests in tests. All evidence is fixture data."""
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.catalog.models import Offer, Product, Shop
from apps.missions.models import PurchaseMission
from apps.missions.neshan_routing import read_matrix


class RouteEstimateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        create = self.client.post("/api/v1/missions/", {
            "initial_message": "هدفون حضوری",
            "constraints": {"lat": 35.7001, "lon": 51.4001},
        }, format="json")
        self.assertEqual(create.status_code, 201)
        self.mission_id = create.json()["mission_id"]
        self.product = Product.objects.create(source_id="p1", persian_title="هدفون نمونه")
        self.shop_a = Shop.objects.create(
            source_id="s1", name="فروشگاه نمونه یک", lat=35.701, lon=51.401,
        )
        self.shop_b = Shop.objects.create(
            source_id="s2", name="فروشگاه نمونه دو", lat=35.702, lon=51.402,
        )
        self.offer_a = Offer.objects.create(source_id="a1", product=self.product, shop=self.shop_a)
        self.offer_b = Offer.objects.create(source_id="a2", product=self.product, shop=self.shop_b)
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        mission.state = {
            "result_set_id": "current-result", "results_stale": False,
            "active_surface": "sellers",
            "selected_product_id": self.product.source_id,
            "visible_offer_ids": [self.offer_a.source_id, self.offer_b.source_id],
        }
        mission.save(update_fields=["state"])
        self.url = f"/api/v1/missions/{self.mission_id}/route-estimates/"
        self.payload = {
            "result_set_id": "current-result",
            "origin": {"lat": 35.7001, "lon": 51.4001, "source": "manual_region"},
            "offer_ids": ["a1", "a2"],
            "mode": "car",
        }

    def test_feature_disabled_by_default_never_contacts_provider(self):
        status = self.client.get(self.url)
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["enabled"])
        with patch("apps.missions.views.read_matrix") as network:
            response = self.client.post(self.url, self.payload, format="json")
            network.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estimates"], [])
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertNotIn("duration_seconds", str(response.json()))

    def test_stale_or_unlisted_offer_and_unapproved_origin_are_blocked(self):
        for changes in (
            {"result_set_id": "old-result"},
            {"offer_ids": ["a1", "unrelated"]},
            {"origin": {"lat": 35.8, "lon": 51.4, "source": "manual_region"}},
            {"origin": {"lat": 52.5, "lon": 13.4, "source": "manual_region"}},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(self.url, {**self.payload, **changes}, format="json")
                self.assertEqual(response.status_code, 400)

    @override_settings(
        NESHAN_ROUTING_ENABLED=True,
        NESHAN_ROUTING_API_KEY="fake-unit-test-key",
        NESHAN_ROUTING_MAX_CALLS_PER_MISSION=1,
        NESHAN_ROUTING_DAILY_MAX_CALLS=2,
    )
    def test_mocked_provider_and_paid_request_cap(self):
        status = self.client.get(self.url).json()
        self.assertTrue(status["enabled"])
        with patch("apps.missions.views.read_matrix", return_value=[
            {"status": "ok", "duration_seconds": 610, "route_distance_meters": 3200},
            {"status": "no_route"},
        ]) as provider:
            answer = self.client.post(self.url, self.payload, format="json")
            self.assertEqual(answer.status_code, 200, answer.content)
            result = answer.json()
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["estimates"][0]["offer_id"], "a1")
            self.assertEqual(result["estimates"][0]["duration_seconds"], 610)
            self.assertNotIn("duration_seconds", result["estimates"][1])
            self.assertFalse(result["availability_verified"])
            limited = self.client.post(self.url, self.payload, format="json")
            self.assertEqual(limited.json()["reason"], "mission_budget_exhausted")
            provider.assert_called_once()
        mission = PurchaseMission.objects.get(pk=self.mission_id)
        self.assertEqual(mission.state["neshan_route_calls"], 1)

    @override_settings(
        NESHAN_ROUTING_ENABLED=True,
        NESHAN_ROUTING_API_KEY="fake-unit-test-key",
        NESHAN_ROUTING_MAX_CALLS_PER_MISSION=5,
        NESHAN_ROUTING_DAILY_MAX_CALLS=1,
    )
    def test_shared_daily_budget_blocks_further_paid_requests(self):
        with patch("apps.missions.views.read_matrix", return_value=[
            {"status": "no_route"}, {"status": "no_route"},
        ]) as provider:
            first = self.client.post(self.url, self.payload, format="json")
            second = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(first.json()["status"], "ok")
        self.assertEqual(second.json()["reason"], "daily_budget_exhausted")
        provider.assert_called_once()

    @override_settings(
        NESHAN_ROUTING_ENABLED=True,
        NESHAN_ROUTING_API_KEY="fake-unit-test-key",
        NESHAN_ROUTING_MAX_CALLS_PER_MISSION=2,
        NESHAN_ROUTING_DAILY_MAX_CALLS=2,
    )
    def test_provider_failure_gives_no_fabricated_eta(self):
        from apps.missions.neshan_routing import RoutingUnavailable
        with patch("apps.missions.views.read_matrix", side_effect=RoutingUnavailable("quota_or_key_unavailable")):
            result = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["estimates"], [])
        self.assertEqual(result.json()["reason"], "quota_or_key_unavailable")

    def test_mission_id_does_not_leak_to_another_session(self):
        self.client = APIClient()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.payload, format="json").status_code, 404)


class MatrixParserTests(TestCase):
    @override_settings(
        NESHAN_ROUTING_ENABLED=True,
        NESHAN_ROUTING_API_KEY="fake-test",
        NESHAN_ROUTING_MAX_CALLS_PER_MISSION=2,
        NESHAN_ROUTING_DAILY_MAX_CALLS=2,
    )
    def test_normalizes_provider_status_without_guessing_unknown_numbers(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps({
            "status": "Ok", "rows": [{"elements": [
                {"status": "Ok", "duration": {"value": 420}, "distance": {"value": 3400}},
                {"status": "NoRoute"},
                {"status": "UnknownError"},
            ]}]
        }).encode()
        context = MagicMock()
        context.__enter__.return_value = response
        opener = MagicMock()
        opener.open.return_value = context
        with patch("apps.missions.neshan_routing.build_opener", return_value=opener):
            result = read_matrix((35.7, 51.4), [(35.71, 51.42), (35.72, 51.43), (35.73, 51.44)], "car")
        self.assertEqual(result[0]["duration_seconds"], 420)
        self.assertEqual(result[1], {"status": "no_route"})
        self.assertEqual(result[2], {"status": "unknown_error"})
        sent_request = opener.open.call_args.args[0]
        self.assertTrue(sent_request.full_url.startswith("https://api.neshan.org/v1/distance-matrix?"))
        self.assertEqual(sent_request.get_header("Api-key"), "fake-test")
