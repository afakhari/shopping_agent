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
