"""Regression tests: credit limits must apply to actual offers, not shop badges."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Offer, Product, Shop
from apps.catalog.services.normalization import normalize_persian_text


class OfferLevelCreditEligibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.shop = Shop.objects.create(
            source_id="s-credit",
            name="فروشگاه تست",
            payment_options=[
                {
                    "channel": "in_person",
                    "provider_name": "نمونه",
                    "min_price_toman": 700000,
                    "max_price_toman": 900000,
                    "category_names": ["هدفون"],
                }
            ],
        )
        self.headphone = Product.objects.create(
            source_id="p-headphone",
            persian_title="هدفون تست",
            normalized_title=normalize_persian_text("هدفون تست"),
            category_name="هدفون",
        )
        self.speaker = Product.objects.create(
            source_id="p-speaker",
            persian_title="اسپیکر تست",
            normalized_title=normalize_persian_text("اسپیکر تست"),
            category_name="اسپیکر",
        )
        for id_, product, price in (
            ("o-cheap", self.headphone, 500000),
            ("o-eligible", self.headphone, 800000),
            ("o-expensive", self.headphone, 1100000),
            ("o-wrong-category", self.speaker, 800000),
        ):
            Offer.objects.create(
                source_id=id_, product=product, shop=self.shop, price_toman=Decimal(price)
            )

    def _offers(self, product_id, **query):
        response = self.client.get(
            f"/api/v1/products/{product_id}/offers/",
            {"must_have_in_person_credit": "true", **query},
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["results"]

    def test_provider_price_and_category_rules_restrict_offers(self):
        self.assertEqual(
            [row["id"] for row in self._offers(self.headphone.source_id)],
            ["o-eligible"],
        )
        self.assertEqual(self._offers(self.speaker.source_id), [])

    def test_catalog_search_reuses_offer_level_policy(self):
        response = self.client.get(
            "/api/v1/catalog/search/",
            {"q": "هدفون", "must_have_in_person_credit": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["results"][0]["best_offer"]["id"], "o-eligible")

    def test_stricter_buyer_budget_does_not_relax_provider_minimum(self):
        self.assertEqual(
            self._offers(self.headphone.source_id, max_price_toman="750000"), []
        )

    def test_second_eligible_provider_is_respected(self):
        self.shop.payment_options.append(
            {"channel": "in_person", "provider_name": "پشتیبان",
             "category_names": [], "max_price_toman": 600000}
        )
        self.shop.save(update_fields=["payment_options"])
        self.assertEqual(
            [row["id"] for row in self._offers(self.headphone.source_id)],
            ["o-cheap", "o-eligible"],
        )

    def test_unknown_channel_and_bad_limits_fail_closed(self):
        self.shop.payment_options = [
            {"channel": "unknown", "category_names": []},
            {"channel": "in_person", "category_names": [],
             "min_price_toman": "not-a-number"},
        ]
        self.shop.save(update_fields=["payment_options"])
        self.assertEqual(self._offers(self.headphone.source_id), [])

    def test_legacy_unbounded_in_person_provider_remains_eligible(self):
        self.shop.payment_options = [{"channel": "in_person", "category_names": []}]
        self.shop.save(update_fields=["payment_options"])
        self.assertEqual(len(self._offers(self.headphone.source_id)), 3)

    def test_missing_offer_price_cannot_satisfy_positive_minimum(self):
        Offer.objects.create(
            source_id="o-no-price", product=self.headphone, shop=self.shop,
            price_toman=None,
        )
        self.assertEqual(
            [row["id"] for row in self._offers(self.headphone.source_id)],
            ["o-eligible"],
        )

    def test_seller_warranty_and_registered_title_are_returned(self):
        offer = Offer.objects.get(pk="o-eligible")
        offer.seller_title = "هدفون با گارانتی"
        offer.warranty = {"provider": "شرکتی", "period_months": 12}
        offer.save(update_fields=["seller_title", "warranty"])
        selected = self._offers(self.headphone.source_id)[0]
        self.assertEqual(selected["seller_title"], "هدفون با گارانتی")
        self.assertEqual(selected["warranty"]["period_months"], 12)
        self.assertEqual(selected["warranty"]["provider"], "شرکتی")
        self.assertTrue(selected["in_person_credit_eligible"])

    def test_credit_badge_depends_on_offer_not_only_store(self):
        from apps.search.services import serialize_offer

        self.assertFalse(serialize_offer(Offer.objects.get(pk="o-cheap"))["in_person_credit_eligible"])
        self.assertTrue(serialize_offer(Offer.objects.get(pk="o-eligible"))["in_person_credit_eligible"])
        self.assertFalse(serialize_offer(Offer.objects.get(pk="o-wrong-category"))["in_person_credit_eligible"])

 
