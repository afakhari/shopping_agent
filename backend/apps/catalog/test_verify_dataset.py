"""Small Django command tests using fixtures, not private competition data."""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.catalog.models import Offer, Product, Shop


class VerifyDatasetCommandTests(TestCase):
    def test_empty_database_fails(self):
        with self.assertRaisesMessage(CommandError, "table is empty"):
            call_command("verify_dataset", stdout=StringIO())

    def test_valid_fixture_counts_pass(self):
        product = Product.objects.create(source_id="p-test", persian_title="نمونه")
        shop = Shop.objects.create(source_id="s-test", name="فروشگاه آزمایشی")
        Offer.objects.create(
            source_id="o-test", product=product, shop=shop, price_toman=Decimal("120000")
        )
        output = StringIO()
        call_command(
            "verify_dataset", products=1, shops=1, offers=1,
            sample_product="p-test", sample_shop="s-test", sample_offer="o-test",
            json=True, stdout=output,
        )
        self.assertIn('"status": "ok"', output.getvalue())

    def test_mismatched_count_fails(self):
        Product.objects.create(source_id="p-test", persian_title="نمونه")
        with self.assertRaisesMessage(CommandError, "expected 2, found 1"):
            call_command("verify_dataset", products=2, stdout=StringIO())

    def test_missing_sample_fails_even_when_counts_match(self):
        product = Product.objects.create(source_id="p-test", persian_title="نمونه")
        shop = Shop.objects.create(source_id="s-test", name="فروشگاه آزمایشی")
        Offer.objects.create(
            source_id="o-test", product=product, shop=shop, price_toman=Decimal("100")
        )
        with self.assertRaisesMessage(CommandError, "sample product missing"):
            call_command(
                "verify_dataset", products=1, shops=1, offers=1,
                sample_product="p-other", stdout=StringIO(),
            )
