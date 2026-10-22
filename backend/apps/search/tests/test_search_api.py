from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Offer, Product, Shop
from apps.catalog.services.normalization import normalize_persian_text


class CatalogSearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.credit_shop = Shop.objects.create(
            source_id="shop_credit",
            name="فروشگاه اعتباری",
            address="تهران، خیابان نمونه، پاساژ مثال، طبقه دوم، واحد ۲۱",
            location_label="مرکز تهران",
            lat=35.7000,
            lon=51.4000,
            payment_options=[{"provider_name": "ترب‌پی", "channel": "in_person"}],
        )
        self.cash_shop = Shop.objects.create(
            source_id="shop_cash",
            name="فروشگاه نقدی",
            address="تهران، خیابان دیگر",
            lat=35.8000,
            lon=51.4000,
            payment_options=[],
        )
        self.headphone = Product.objects.create(
            source_id="product_headphone",
            persian_title="هدفون بی‌سیم سونی مدل نمونه",
            normalized_title=normalize_persian_text("هدفون بی‌سیم سونی مدل نمونه"),
            brand_name="سونی",
            category_name="هدفون",
            model="WH-DEMO",
            specs=[{"key": "نوع اتصال", "section": "مشخصات", "value": "بی‌سیم"}],
            image_urls=["https://example.com/headphone.jpg"],
        )
        self.wired_headphone = Product.objects.create(
            source_id="product_wired",
            persian_title="هدفون سیمی ساده",
            normalized_title=normalize_persian_text("هدفون سیمی ساده"),
            category_name="هدفون",
        )
        Product.objects.create(
            source_id="product_without_offer",
            persian_title="هدفون بدون آفر فروشگاهی",
            normalized_title=normalize_persian_text("هدفون بدون آفر فروشگاهی"),
            category_name="هدفون",
        )
        self.outlier_product = Product.objects.create(
            source_id="product_outlier",
            persian_title="تلویزیون با قیمت پرت",
            normalized_title=normalize_persian_text("تلویزیون با قیمت پرت"),
            category_name="تلویزیون",
        )
        self.credit_offer = Offer.objects.create(
            source_id="offer_credit",
            product=self.headphone,
            shop=self.credit_shop,
            price_toman=Decimal("900000"),
        )
        self.cash_offer = Offer.objects.create(
            source_id="offer_cash",
            product=self.headphone,
            shop=self.cash_shop,
            price_toman=Decimal("500000"),
        )
        self.wired_offer = Offer.objects.create(
            source_id="offer_wired",
            product=self.wired_headphone,
            shop=self.cash_shop,
            price_toman=Decimal("650000"),
        )
        Offer.objects.create(
            source_id="offer_outlier",
            product=self.outlier_product,
            shop=self.cash_shop,
            price_toman=Decimal("100000000001"),
        )
        # A measured ambiguity in the real dataset: the same word is used for
        # consumer blood-pressure monitors and industrial/environmental gauges.
        self.medical_pressure = Product.objects.create(
            source_id="product_pressure_medical",
            persian_title="فشارسنج دیجیتالی خانگی نمونه",
            normalized_title=normalize_persian_text("فشارسنج دیجیتالی خانگی نمونه"),
            category_name="فشارسنج پزشکی",
        )
        self.industrial_pressure = Product.objects.create(
            source_id="product_pressure_industrial",
            persian_title="فشارسنج ناتالی ۱۰ بار سایز ۵ سانتی",
            normalized_title=normalize_persian_text("فشارسنج ناتالی ۱۰ بار سایز ۵ سانتی"),
            category_name="بارومتر و فشارسنج محیطی",
        )
        Offer.objects.create(
            source_id="offer_pressure_medical",
            product=self.medical_pressure,
            shop=self.cash_shop,
            price_toman=Decimal("950000"),
        )
        Offer.objects.create(
            source_id="offer_pressure_industrial",
            product=self.industrial_pressure,
            shop=self.cash_shop,
            price_toman=Decimal("600000"),
        )

    def test_search_returns_only_products_with_matching_offers(self):
        response = self.client.get("/api/v1/catalog/search/", {"q": "هدفون"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(len(body["results"]), 2)
        self.assertTrue(all(item["best_offer"]["shop"]["id"] for item in body["results"]))

    def test_budget_hard_filter_accepts_persian_digits(self):
        response = self.client.get(
            "/api/v1/catalog/search/",
            {"q": "هدفون", "max_price_toman": "۸۰۰۰۰۰", "sort": "price_asc"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], 2)
        result_by_id = {row["product"]["id"]: row for row in body["results"]}
        self.assertEqual(result_by_id["product_headphone"]["best_offer"]["price_toman"], "500000")
        self.assertEqual(result_by_id["product_wired"]["best_offer"]["price_toman"], "650000")

    def test_in_person_credit_is_a_hard_filter(self):
        response = self.client.get(
            "/api/v1/catalog/search/",
            {"q": "هدفون", "must_have_in_person_credit": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["results"][0]["product"]["id"], "product_headphone")
        self.assertEqual(body["results"][0]["best_offer"]["shop"]["id"], "shop_credit")
        self.assertEqual(body["results"][0]["best_offer"]["price_toman"], "900000")

    def test_budget_and_credit_constraints_are_both_applied(self):
        response = self.client.get(
            "/api/v1/catalog/search/",
            {"q": "هدفون", "max_price_toman": "800000", "must_have_in_person_credit": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_radius_removes_shops_outside_user_selected_area(self):
        response = self.client.get(
            "/api/v1/catalog/search/",
            {"q": "هدفون", "lat": "35.7000", "lon": "51.4000", "radius_m": "5000"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["results"][0]["product"]["id"], "product_headphone")

    def test_distance_sort_requires_origin(self):
        response = self.client.get(
            "/api/v1/catalog/search/", {"q": "هدفون", "sort": "distance_asc"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_radius_requires_both_coordinates(self):
        response = self.client.get(
            "/api/v1/catalog/search/", {"q": "هدفون", "lat": "35.7", "radius_m": "5000"}
        )
        self.assertEqual(response.status_code, 400)

    def test_product_offers_use_same_credit_filter(self):
        response = self.client.get(
            f"/api/v1/products/{self.headphone.source_id}/offers/",
            {"must_have_in_person_credit": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["results"][0]["shop"]["id"], "shop_credit")

    def test_shop_detail_preserves_unknown_values(self):
        response = self.client.get(f"/api/v1/shops/{self.cash_shop.source_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        shop = response.json()["shop"]
        self.assertIsNone(shop["supports_fast_delivery"])
        self.assertEqual(shop["payment_options"], [])

    def test_extreme_price_outliers_are_not_ranked_as_shoppable_results(self):
        response = self.client.get("/api/v1/catalog/search/", {"q": "تلویزیون"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_pagination_is_applied_after_unique_product_filtering(self):
        response = self.client.get(
            "/api/v1/catalog/search/", {"q": "هدفون", "page": "2", "page_size": "1"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 2)
        self.assertEqual(response.json()["page"], 2)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_price_quality_distinguishes_stale_price_from_stock(self):
        stale_at = timezone.now() - timedelta(days=8)
        self.credit_offer.last_price_changed_at = stale_at
        self.credit_offer.save(update_fields=["last_price_changed_at"])
        self.cash_offer.last_price_changed_at = stale_at
        self.cash_offer.save(update_fields=["last_price_changed_at"])
        response = self.client.get("/api/v1/catalog/search/", {"q": "هدفون"})
        self.assertEqual(response.status_code, 200, response.content)
        results = {item["product"]["id"]: item for item in response.json()["results"]}
        self.assertEqual(results["product_headphone"]["best_offer"]["price_quality"], "stale")

    def test_price_without_timestamp_is_not_called_fresh(self):
        response = self.client.get("/api/v1/catalog/search/", {"q": "هدفون"})
        self.assertEqual(response.status_code, 200, response.content)
        results = {item["product"]["id"]: item for item in response.json()["results"]}
        self.assertEqual(
            results["product_headphone"]["best_offer"]["price_quality"], "unknown_timestamp"
        )

    def test_shop_credit_flag_stays_synced_on_regular_save(self):
        self.cash_shop.payment_options = [{"channel": "in_person", "provider_name": "نمونه"}]
        self.cash_shop.save(update_fields=["payment_options"])
        self.cash_shop.refresh_from_db()
        self.assertTrue(self.cash_shop.accepts_in_person_credit)

    def test_unmatched_query_is_empty_instead_of_showing_ineligible_items(self):
        response = self.client.get("/api/v1/catalog/search/", {"q": "ماشین پرنده"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["results"], [])
        self.assertEqual(response.json()["total"], 0)

    def test_bare_pressure_gauge_query_defaults_to_medical_category_and_offers_alternative(self):
        response = self.client.get("/api/v1/catalog/search/", {"q": "فشارسنج"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["results"][0]["product"]["id"], "product_pressure_medical")
        self.assertEqual(body["intent_hint"]["label"], "فشارسنج پزشکی")
        self.assertEqual(body["intent_hint"]["alternative_query"], "فشارسنج صنعتی")

    def test_explicit_industrial_pressure_query_uses_industrial_categories(self):
        response = self.client.get("/api/v1/catalog/search/", {"q": "فشارسنج صنعتی"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["results"][0]["product"]["id"], "product_pressure_industrial")
        self.assertIsNone(body["intent_hint"])

    def test_specific_pressure_model_query_is_not_silently_scoped(self):
        response = self.client.get(
            "/api/v1/catalog/search/", {"q": "فشارسنج ناتالی ۱۰ بار سایز ۵ سانتی"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        # Specific product/model queries remain broad, but the full phrase match ranks first.
        self.assertGreaterEqual(body["total"], 2)
        self.assertEqual(body["results"][0]["product"]["id"], "product_pressure_industrial")
        self.assertIsNone(body["intent_hint"])
