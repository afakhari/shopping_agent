from pathlib import Path

from django.test import SimpleTestCase, TestCase

from apps.catalog.management.commands.import_dataset import (
    parse_coordinate,
    parse_decimal_price,
    parse_json_cell,
    parse_nullable_bool,
    parse_nullable_text,
    parse_timestamp,
)
from apps.catalog.services.normalization import normalize_persian_text


class PersianNormalizationTests(SimpleTestCase):
    def test_normalizes_arabic_letters_digits_and_spacing(self):
        self.assertEqual(normalize_persian_text("كیف ياس ۱۲۳ ٤٥"), "کیف یاس 123 45")

    def test_normalizes_zwnj_without_destroying_display_source(self):
        self.assertEqual(normalize_persian_text("بی‌سیم   هدفون"), "بی سیم هدفون")

    def test_empty_input(self):
        self.assertEqual(normalize_persian_text("  "), "")


class ImportParserTests(SimpleTestCase):
    def test_null_like_values_are_handled_explicitly(self):
        self.assertIsNone(parse_nullable_text("null"))
        self.assertIsNone(parse_nullable_text("   "))
        self.assertEqual(parse_nullable_text(" کالا "), "کالا")

    def test_json_parser_accepts_null_and_rejects_wrong_shapes(self):
        self.assertEqual(parse_json_cell("null", list, [])[0], [])
        self.assertEqual(parse_json_cell('["الف"]', list, [])[0], ["الف"])
        self.assertEqual(parse_json_cell('{"bad": true}', list, [])[1], True)
        self.assertEqual(parse_json_cell("{broken", dict, {})[1], True)

    def test_decimal_parser_avoids_float_and_handles_persian_digits(self):
        value, invalid = parse_decimal_price("۱۲۳۴۵۶")
        self.assertFalse(invalid)
        self.assertEqual(str(value), "123456")
        self.assertEqual(parse_decimal_price("1.5")[1], True)
        self.assertEqual(parse_decimal_price("null"), (None, False))

    def test_timestamp_parser_returns_aware_datetime(self):
        parsed, invalid = parse_timestamp("2026-10-13T10:00:00+00:00")
        self.assertFalse(invalid)
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parse_timestamp("not-a-date")[1], True)

    def test_coordinate_and_nullable_boolean_parsers(self):
        self.assertEqual(parse_coordinate("35.7"), (35.7, False))
        self.assertEqual(parse_coordinate("null"), (None, False))
        self.assertEqual(parse_nullable_bool("true"), (True, False))
        self.assertEqual(parse_nullable_bool("null"), (None, False))

    def test_coordinate_parser_range_is_enforced_by_field_context(self):
        self.assertEqual(parse_coordinate("181"), (None, True))
        self.assertEqual(parse_coordinate("-181"), (None, True))

class DatasetImportCommandTests(TestCase):
    """The importer must support a reproducible small ZIP fixture and safe re-runs."""

    def _build_archive(self, directory):
        import csv
        import zipfile
        archive_path = Path(directory) / "fixture.zip"
        fixtures = {
            "products.csv": [
                [
                    "brand_name", "category_name", "image_urls", "model", "persian_title",
                    "product_id", "specs",
                ],
                [
                    "سونی", "هدفون", "[]", "DEMO", "هدفون نمونه", "product_1",
                    '[{"key":"نوع","value":"بی‌سیم"}]',
                ],
            ],
            "shops.csv": [
                [
                    "address", "category_names", "contacts", "instagram", "lat",
                    "location_label", "lon", "name", "payment_options", "shop_id",
                    "supports_fast_delivery", "website_url", "weekly_hours",
                ],
                [
                    "تهران، خیابان نمونه", '["هدفون"]',
                    '[{"channel":"phone","display_number":"۰۲۱۱۲۳۴۵۶۷۸"}]', "null",
                    "35.7", "مرکز تهران", "51.4", "فروشگاه نمونه", '[{"channel":"in_person"}]',
                    "shop_1", "null", "null", "{}",
                ],
            ],
            "offers.csv": [
                [
                    "description", "last_price_changed_at", "offer_id", "price_toman",
                    "product_id", "seller_title", "shop_id", "warranty",
                ],
                [
                    "", "2026-10-13T10:00:00+00:00", "offer_1", "1250000", "product_1",
                    "هدفون نمونه", "shop_1", "null",
                ],
            ],
        }
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, rows in fixtures.items():
                from io import StringIO

                buffer = StringIO()
                csv.writer(buffer).writerows(rows)
                archive.writestr(name, buffer.getvalue())
        return archive_path

    def test_import_is_idempotent(self):
        import tempfile
        from io import StringIO
        from django.core.management import call_command
        from apps.catalog.models import Offer, Product, Shop

        with tempfile.TemporaryDirectory() as directory:
            archive_path = self._build_archive(directory)
            call_command(
                "import_dataset", archive=archive_path,
                report_dir=Path(directory) / "reports", stdout=StringIO(),
            )
            self.assertEqual(Product.objects.count(), 1)
            self.assertEqual(Shop.objects.count(), 1)
            self.assertEqual(Offer.objects.count(), 1)
            self.assertEqual(str(Offer.objects.get().price_toman), "1250000")
            self.assertTrue(Shop.objects.get().accepts_in_person_credit)
            call_command(
                "import_dataset", archive=archive_path,
                report_dir=Path(directory) / "reports", stdout=StringIO(),
            )
            self.assertEqual(Product.objects.count(), 1)
            self.assertEqual(Shop.objects.count(), 1)
            self.assertEqual(Offer.objects.count(), 1)

    def test_dry_run_does_not_write_rows(self):
        import tempfile
        from io import StringIO
        from django.core.management import call_command
        from apps.catalog.models import Offer, Product, Shop

        with tempfile.TemporaryDirectory() as directory:
            archive_path = self._build_archive(directory)
            call_command(
                "import_dataset", archive=archive_path,
                report_dir=Path(directory) / "reports", dry_run=True, stdout=StringIO(),
            )
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(Shop.objects.count(), 0)
        self.assertEqual(Offer.objects.count(), 0)
