"""Contract tests for evidence-driven, abstaining laptop recommendations."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.search.evidence import editing_laptop_evidence


class EditingEvidenceTests(SimpleTestCase):
    def test_structured_usecase_ram_and_ssd_are_explained(self):
        product = SimpleNamespace(
            persian_title="لپ تاپ لنوو نمونه",
            specs=[
                {"key": "کاربری", "value": "برنامه نویسی, تدوین, مالتی مدیا"},
                {"key": "مقدار حافظه رم", "value": "16GB"},
                {"key": "نوع حافظه", "value": "SSD"},
            ],
        )
        result = editing_laptop_evidence(product, intensity="light")
        self.assertTrue(result["usage_declared"])
        self.assertEqual(result["ram_gb"], 16)
        self.assertEqual(result["ram_source"], "spec")
        self.assertTrue(result["ssd_stated"])
        self.assertFalse(result["suitability_verified"])
        self.assertTrue(any("Adobe Premiere" in note for note in result["notes"]))

    def test_light_and_heavy_workflows_have_different_recommendation_refs(self):
        product = SimpleNamespace(
            persian_title="لپ تاپ ایسوس با رم 16GB RAM",
            specs=[{"key": "مقدار حافظه رم", "value": "16GB"}],
        )
        light = editing_laptop_evidence(product, intensity="light")
        heavy = editing_laptop_evidence(product, intensity="heavy")
        self.assertEqual(light["ram_gb"], 16)
        self.assertIn("HD", " ".join(light["notes"]))
        self.assertIn("4K", " ".join(heavy["notes"]))
        self.assertTrue(any("کمتر از" in x for x in heavy["notes"]))
        self.assertFalse(light["suitability_verified"])
        self.assertFalse(heavy["suitability_verified"])

    def test_missing_ram_is_unknown_not_falsely_rejected_or_verified(self):
        product = SimpleNamespace(
            persian_title="لپ تاپ SSD 512GB", specs=[],
        )
        result = editing_laptop_evidence(product, intensity="light")
        self.assertIsNone(result["ram_gb"])
        self.assertTrue(result["ssd_stated"])
        self.assertTrue(any("مشخص نیست" in note for note in result["notes"]))
        self.assertFalse(result["suitability_verified"])

    def test_title_fallback_only_counts_ram_not_ssd_or_gpu(self):
        product = SimpleNamespace(
            persian_title="لپ تاپ LOQ 24GB RAM 512GB SSD RTX 4050",
            specs=[{"key": "نوع حافظه", "value": "SSD"}],
        )
        result = editing_laptop_evidence(product)
        self.assertEqual(result["ram_gb"], 24)
        self.assertEqual(result["ram_source"], "title")
        ssd_only = editing_laptop_evidence(SimpleNamespace(
            persian_title="لپ تاپ 512GB SSD", specs=[],
        ))
        self.assertIsNone(ssd_only["ram_gb"])

    def test_fabricated_field_cannot_infer_ram(self):
        result = editing_laptop_evidence(SimpleNamespace(
            persian_title="لپ تاپ",
            specs=[
                {"key": "حافظه گرافیکی", "value": "8GB"},
                {"key": "قابلیت ارتقاء رم", "value": "Up to 64GB"},
            ],
        ))
        self.assertIsNone(result["ram_gb"])
        self.assertFalse(result["suitability_verified"])
