from django.test import Client, SimpleTestCase, TestCase, override_settings


class LivenessTests(SimpleTestCase):
    def test_liveness_is_available_without_database_access(self):
        response = Client().get("/api/v1/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})

    def test_liveness_rejects_non_get(self):
        response = Client().post("/api/v1/health/live/")
        self.assertEqual(response.status_code, 405)


class ReadinessTests(TestCase):
    def test_readiness_checks_database(self):
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(response.json()["checks"], {"database": "ok"})
        self.assertIn(response.json()["agent_mode"], {"model_configured", "deterministic_fallback"})
        self.assertIn(response.json()["llm"]["status"], {
            "disabled", "unsupported_provider", "missing_api_key", "missing_model",
            "invalid_base_url", "configured",
        })

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="openai_compatible",
        LLM_API_KEY="test-secret-do-not-return",
        LLM_MODEL="test-model",
    )
    def test_readiness_reports_model_configuration_without_disclosing_secret(self):
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent_mode"], "model_configured")
        self.assertEqual(body["llm"]["status"], "configured")
        self.assertTrue(body["llm"]["api_key_present"])
        self.assertTrue(body["llm"]["model_present"])
        self.assertNotIn("test-secret-do-not-return", response.content.decode("utf-8"))
        self.assertNotIn("test-model", response.content.decode("utf-8"))
        self.assertNotIn("llm.example.test", response.content.decode("utf-8"))

    @override_settings(
        LLM_ENABLED=True,
        LLM_PROVIDER="openai_compatible",
        LLM_API_KEY="",
        LLM_MODEL="",
    )
    def test_readiness_marks_missing_provider_credentials_as_fallback(self):
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["agent_mode"], "deterministic_fallback")
        self.assertEqual(response.json()["llm"]["status"], "missing_api_key")
        self.assertFalse(response.json()["llm"]["api_key_present"])


@override_settings(REQUIRE_DATASET_FOR_READINESS=True)
class ProductionDatasetReadinessTests(TestCase):
    def test_empty_catalog_is_not_ready(self):
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"], {"database": "ok", "catalog": "incomplete"})

    def test_incomplete_catalog_is_not_ready(self):
        from apps.catalog.models import Product

        Product.objects.create(source_id="p1", persian_title="نمونه")
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["catalog"], "incomplete")

    @override_settings(CATALOG_MINIMUM_ROWS={"products": 2, "shops": 1, "offers": 1})
    def test_partial_fixture_is_not_a_ready_full_catalog(self):
        from decimal import Decimal
        from apps.catalog.models import Offer, Product, Shop

        product = Product.objects.create(source_id="part_p", persian_title="نمونه")
        shop = Shop.objects.create(source_id="part_s", name="نمونه")
        Offer.objects.create(source_id="part_o", product=product, shop=shop,
                             price_toman=Decimal("100"))
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["catalog"], "incomplete")

    def test_linked_catalog_is_ready(self):
        from decimal import Decimal

        from apps.catalog.models import Offer, Product, Shop

        product = Product.objects.create(source_id="p1", persian_title="نمونه")
        shop = Shop.objects.create(source_id="s1", name="فروشگاه نمونه")
        Offer.objects.create(source_id="o1", product=product, shop=shop, price_toman=Decimal("100"))
        response = Client().get("/api/v1/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"], {"database": "ok", "catalog": "ok"})
