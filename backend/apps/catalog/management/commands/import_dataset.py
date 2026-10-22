"""Idempotently import the challenge CSVs without loading entire files into RAM.

Examples:
  python manage.py import_dataset --archive /path/to/dataset.zip --dry-run
  python manage.py import_dataset --archive /path/to/dataset.zip
  python manage.py import_dataset --input-dir /app/data/raw
"""
from __future__ import annotations

import csv
import io
import json
import time
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator, TextIO

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.catalog.models import Offer, Product, Shop, has_in_person_credit
from apps.catalog.services.normalization import normalize_persian_text


CSV_FILES = ("products.csv", "shops.csv", "offers.csv")
ID_FIELDS = {
    "products.csv": "product_id",
    "shops.csv": "shop_id",
    "offers.csv": "offer_id",
}
EXPECTED_HEADERS = {
    "products.csv": {
        "product_id", "persian_title", "brand_name", "category_name", "model", "specs", "image_urls"
    },
    "shops.csv": {
        "shop_id", "name", "address", "category_names", "contacts", "instagram", "lat",
        "location_label", "lon", "payment_options", "supports_fast_delivery", "website_url",
        "weekly_hours",
    },
    "offers.csv": {
        "offer_id", "product_id", "shop_id", "price_toman", "last_price_changed_at",
        "seller_title", "description", "warranty",
    },
}
JSON_FIELDS: dict[str, dict[str, tuple[type, Any]]] = {
    "products.csv": {"specs": (list, list), "image_urls": (list, list)},
    "shops.csv": {
        "category_names": (list, list),
        "contacts": (list, list),
        "payment_options": (list, list),
        "weekly_hours": (dict, dict),
    },
    "offers.csv": {"warranty": (dict, None)},
}


def parse_nullable_text(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value or value.casefold() == "null":
        return None
    return value


def parse_json_cell(raw: str | None, expected_type: type, default: Any) -> tuple[Any, bool]:
    """Return (parsed value, was_invalid); tolerate blank and literal-null cells."""
    value = parse_nullable_text(raw)
    if value is None:
        return default, False
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default, True
    if parsed is None:
        return default, False
    if not isinstance(parsed, expected_type):
        return default, True
    return parsed, False


def parse_decimal_price(raw: str | None) -> tuple[Decimal | None, bool]:
    value = parse_nullable_text(raw)
    if value is None:
        return None, False
    try:
        digit_map = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
        )
        amount = Decimal(value.translate(digit_map))
    except (InvalidOperation, ValueError):
        return None, True
    if not amount.is_finite() or amount != amount.to_integral_value():
        return None, True
    return amount, False


def parse_timestamp(raw: str | None) -> tuple[datetime | None, bool]:
    value = parse_nullable_text(raw)
    if value is None:
        return None, False
    try:
        parsed = parse_datetime(value)
    except (TypeError, ValueError, OverflowError):
        parsed = None
    if parsed is None:
        return None, True
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed, False


def parse_coordinate(raw: str | None) -> tuple[float | None, bool]:
    value = parse_nullable_text(raw)
    if value is None:
        return None, False
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None, True
    if not (-180 <= parsed <= 180):
        return None, True
    return parsed, False


def parse_nullable_bool(raw: str | None) -> tuple[bool | None, bool]:
    value = parse_nullable_text(raw)
    if value is None:
        return None, False
    if value.casefold() in {"true", "1", "yes"}:
        return True, False
    if value.casefold() in {"false", "0", "no"}:
        return False, False
    return None, True


class DatasetReader:
    """Open the CSVs either from a directory or directly from a ZIP archive."""

    def __init__(self, input_dir: Path | None, archive_path: Path | None):
        self.input_dir = input_dir
        self.archive_path = archive_path

    @contextmanager
    def open_csv(self, name: str) -> Iterator[TextIO]:
        if self.archive_path:
            try:
                with zipfile.ZipFile(self.archive_path) as archive:
                    candidates = [
                        item for item in archive.namelist()
                        if item.rsplit("/", 1)[-1] == name
                    ]
                    if len(candidates) != 1:
                        raise CommandError(
                            f"Expected exactly one {name} in archive; found {len(candidates)}."
                        )
                    with archive.open(candidates[0], "r") as raw:
                        with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text_stream:
                            yield text_stream
            except (OSError, zipfile.BadZipFile) as exc:
                raise CommandError(f"Cannot read archive {self.archive_path}: {exc}") from exc
        else:
            if not self.input_dir:
                raise CommandError("Provide --archive or --input-dir.")
            path = self.input_dir / name
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as stream:
                    yield stream
            except OSError as exc:
                raise CommandError(f"Cannot read {path}: {exc}") from exc

    def rows(self, name: str) -> Iterator[dict[str, str]]:
        with self.open_csv(name) as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise CommandError(f"{name} has no CSV header.")
            missing = EXPECTED_HEADERS[name].difference(reader.fieldnames)
            if missing:
                missing_text = ", ".join(sorted(missing))
                raise CommandError(f"{name} is missing required columns: {missing_text}")
            for row in reader:
                yield row


class Command(BaseCommand):
    help = (
        "Import products.csv, shops.csv and offers.csv idempotently "
        "from a directory or ZIP archive."
    )

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument(
            "--archive", type=Path, help="Path to the provided dataset ZIP archive."
        )
        source.add_argument(
            "--input-dir", type=Path, help="Directory containing the three CSV files."
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=getattr(settings, "DATASET_IMPORT_BATCH_SIZE", 2000),
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Validate the archive and report counts without DB writes.",
        )
        parser.add_argument(
            "--allow-orphans", action="store_true",
            help="Skip offers whose product/shop is missing, and report them.",
        )
        parser.add_argument(
            "--strict-json", action="store_true",
            help="Abort if a nested JSON cell is malformed or wrong-shaped.",
        )
        parser.add_argument(
            "--report-dir", type=Path, default=None,
            help="Directory for JSON and Markdown audit reports; defaults to DATASET_REPORT_DIR.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size < 1 or batch_size > 20000:
            raise CommandError("--batch-size must be between 1 and 20000.")

        archive = options["archive"]
        input_dir = options["input_dir"]
        if archive and not archive.is_file():
            raise CommandError(f"Archive does not exist: {archive}")
        if input_dir and not input_dir.is_dir():
            raise CommandError(f"Input directory does not exist: {input_dir}")
        reader = DatasetReader(input_dir, archive)
        started_clock = time.monotonic()
        started_at = datetime.now(datetime_timezone.utc)
        report_dir = options["report_dir"] or settings.DATASET_REPORT_DIR
        source_label = archive.name if archive else f"directory:{input_dir.name}"
        self.stdout.write("Preflight: validating IDs, references and nested values...")
        report, product_ids, shop_ids = self._preflight(reader)
        self._print_report(report)

        failure_message = None
        if report["duplicate_ids"] or report["missing_ids"]:
            failure_message = (
                "Preflight failed: duplicate source IDs or missing IDs detected. "
                "No database writes were performed."
            )
        elif report["orphan_offers"] and not options["allow_orphans"]:
            failure_message = (
                f"Preflight failed: {report['orphan_offers']} offers reference "
                "unknown products/shops. "
                "No database writes were performed. "
                "Use --allow-orphans only if skipping is intentional."
            )
        elif options["strict_json"] and report["invalid_json_cells"]:
            failure_message = (
                f"Preflight failed: {report['invalid_json_cells']} invalid JSON cells found. "
                "No writes performed."
            )
        if failure_message:
            self._write_reports(
                report_dir, source_label, started_at, "preflight_failed", {}, report,
                time.monotonic() - started_clock,
            )
            raise CommandError(failure_message)

        if options["dry_run"]:
            elapsed = time.monotonic() - started_clock
            self._write_reports(
                report_dir, source_label, started_at, "dry_run_complete", {}, report, elapsed
            )
            self.stdout.write(self.style.SUCCESS("Dry run complete; database was not modified."))
            self.stdout.write(f"Audit report directory: {report_dir}")
            return

        counters = Counter()
        try:
            counters.update(self._import_products(reader, batch_size))
            counters.update(self._import_shops(reader, batch_size))
            counters.update(
                self._import_offers(
                    reader, batch_size, product_ids, shop_ids, options["allow_orphans"]
                )
            )
        except Exception:
            elapsed = time.monotonic() - started_clock
            self._write_reports(
                report_dir, source_label, started_at, "import_failed_partial_batches_possible",
                dict(counters), report, elapsed,
            )
            raise

        elapsed = time.monotonic() - started_clock
        self._write_reports(
            report_dir, source_label, started_at, "import_complete", dict(counters), report, elapsed
        )
        self.stdout.write("\nImport summary")
        summary_keys = (
            "products_inserted", "products_updated", "shops_inserted", "shops_updated",
            "offers_inserted", "offers_updated", "offers_skipped_orphan",
        )
        for key in summary_keys:
            self.stdout.write(f"  {key}: {counters.get(key, 0):,}")
        self.stdout.write(f"  elapsed_seconds: {elapsed:.2f}")
        self.stdout.write(f"  audit_report_dir: {report_dir}")
        self.stdout.write(
            self.style.SUCCESS("Dataset import finished. Re-running is safe and idempotent.")
        )

    def _write_reports(
        self, report_dir, source_label, started_at, status, import_counters, preflight, elapsed
    ):
        report_dir.mkdir(parents=True, exist_ok=True)
        completed_at = datetime.now(datetime_timezone.utc)
        payload = {
            "report_version": 1,
            "source": source_label,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "status": status,
            "elapsed_seconds": round(elapsed, 3),
            "preflight": dict(preflight),
            "import": import_counters,
        }
        stamp = completed_at.strftime("%Y%m%dT%H%M%S%fZ")
        json_path = report_dir / f"dataset-import-{stamp}.json"
        markdown_path = report_dir / f"dataset-import-{stamp}.md"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# گزارش ورود دیتاست",
            "",
            f"- وضعیت: `{status}`",
            f"- منبع: `{source_label}`",
            f"- آغاز: `{started_at.isoformat()}`",
            f"- پایان: `{completed_at.isoformat()}`",
            f"- مدت اجرا: `{elapsed:.3f}` ثانیه",
            "",
            "## Preflight",
            "",
            "| شاخص | مقدار |",
            "|---|---:|",
        ]
        lines.extend(f"| `{key}` | {value} |" for key, value in sorted(preflight.items()))
        lines.extend(["", "## عملیات دیتابیس", "", "| شاخص | مقدار |", "|---|---:|"])
        lines.extend(f"| `{key}` | {value} |" for key, value in sorted(import_counters.items()))
        lines.append("")
        markdown_path.write_text("\n".join(lines), encoding="utf-8")

    def _preflight(self, reader: DatasetReader):
        report = Counter()
        seen: dict[str, set[str]] = {name: set() for name in CSV_FILES}
        # Alias the duplicate-detection sets to avoid holding duplicate hash tables
        # for all product/shop IDs during the preflight scan.
        product_ids = seen["products.csv"]
        shop_ids = seen["shops.csv"]
        for filename in CSV_FILES:
            id_field = ID_FIELDS[filename]
            row_count = 0
            for row in reader.rows(filename):
                row_count += 1
                source_id = parse_nullable_text(row.get(id_field))
                if not source_id:
                    report["missing_ids"] += 1
                    continue
                if source_id in seen[filename]:
                    report["duplicate_ids"] += 1
                else:
                    seen[filename].add(source_id)
                # product_ids/shop_ids alias seen[filename], so IDs are already recorded.
                for field, (expected_type, default) in JSON_FIELDS[filename].items():
                    _, invalid = parse_json_cell(row.get(field), expected_type, default)
                    if invalid:
                        report[f"invalid_json:{filename}:{field}"] += 1
                        report["invalid_json_cells"] += 1
                if filename == "offers.csv":
                    parsed_price, invalid_price = parse_decimal_price(row.get("price_toman"))
                    _, invalid_datetime = parse_timestamp(row.get("last_price_changed_at"))
                    if invalid_price:
                        report["invalid_price_values"] += 1
                    elif parsed_price is not None and parsed_price <= 0:
                        report["nonpositive_price_values"] += 1
                    elif (
                        parsed_price is not None
                        and parsed_price > getattr(
                            settings, "MAX_REASONABLE_PRICE_TOMAN", 100_000_000_000
                        )
                    ):
                        report["outlier_price_values"] += 1
                    if invalid_datetime:
                        report["invalid_timestamp_values"] += 1
                if filename == "shops.csv":
                    for coordinate in ("lat", "lon"):
                        parsed_coordinate, invalid = parse_coordinate(row.get(coordinate))
                        if (
                            coordinate == "lat"
                            and parsed_coordinate is not None
                            and not -90 <= parsed_coordinate <= 90
                        ):
                            invalid = True
                        if invalid:
                            report["invalid_coordinates"] += 1
                    _, invalid_bool = parse_nullable_bool(row.get("supports_fast_delivery"))
                    if invalid_bool:
                        report["invalid_boolean_values"] += 1
            report[f"rows:{filename}"] = row_count

        # IDs are now complete: validate offer foreign keys in a second streaming pass.
        for row in reader.rows("offers.csv"):
            product_id = parse_nullable_text(row.get("product_id"))
            shop_id = parse_nullable_text(row.get("shop_id"))
            if product_id not in product_ids or shop_id not in shop_ids:
                report["orphan_offers"] += 1
        # Report total distinct IDs for easy comparison to the dataset README.
        report["unique_product_ids"] = len(product_ids)
        report["unique_shop_ids"] = len(shop_ids)
        report["unique_offer_ids"] = len(seen["offers.csv"])
        return report, product_ids, shop_ids

    def _print_report(self, report: Counter) -> None:
        self.stdout.write("Preflight summary:")
        for key in sorted(report):
            self.stdout.write(f"  {key}: {report[key]:,}")

    def _batches(self, reader: DatasetReader, filename: str, batch_size: int):
        batch: list[dict[str, str]] = []
        for row in reader.rows(filename):
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _upsert_batch(self, model, objects, fields: list[str], batch_size: int):
        if not objects:
            return 0, 0
        source_ids = [obj.source_id for obj in objects]
        existing = set(
            model.objects.filter(source_id__in=source_ids).values_list("source_id", flat=True)
        )
        with transaction.atomic():
            model.objects.bulk_create(
                objects,
                batch_size=batch_size,
                update_conflicts=True,
                update_fields=fields,
                unique_fields=["source_id"],
            )
        return len(source_ids) - len(existing), len(existing)

    def _import_products(self, reader, batch_size: int):
        inserted = updated = 0
        update_fields = [
            "persian_title", "normalized_title", "brand_name", "category_name", "model",
            "specs", "image_urls",
        ]
        for rows in self._batches(reader, "products.csv", batch_size):
            objects = []
            for row in rows:
                source_id = parse_nullable_text(row.get("product_id"))
                if not source_id:
                    continue
                title = parse_nullable_text(row.get("persian_title")) or ""
                specs, _ = parse_json_cell(row.get("specs"), list, [])
                images, _ = parse_json_cell(row.get("image_urls"), list, [])
                objects.append(Product(
                    source_id=source_id,
                    persian_title=title,
                    normalized_title=normalize_persian_text(title),
                    brand_name=parse_nullable_text(row.get("brand_name")),
                    category_name=parse_nullable_text(row.get("category_name")),
                    model=parse_nullable_text(row.get("model")),
                    specs=specs,
                    image_urls=images,
                ))
            created, changed = self._upsert_batch(Product, objects, update_fields, batch_size)
            inserted += created
            updated += changed
        return {"products_inserted": inserted, "products_updated": updated}

    def _import_shops(self, reader, batch_size: int):
        inserted = updated = 0
        update_fields = [
            "name", "category_names", "address", "location_label", "lat", "lon", "contacts",
            "payment_options", "accepts_in_person_credit", "weekly_hours", "website_url",
            "instagram", "supports_fast_delivery",
        ]
        for rows in self._batches(reader, "shops.csv", batch_size):
            objects = []
            for row in rows:
                source_id = parse_nullable_text(row.get("shop_id"))
                if not source_id:
                    continue
                category_names, _ = parse_json_cell(row.get("category_names"), list, [])
                contacts, _ = parse_json_cell(row.get("contacts"), list, [])
                payment_options, _ = parse_json_cell(row.get("payment_options"), list, [])
                weekly_hours, _ = parse_json_cell(row.get("weekly_hours"), dict, {})
                lat, _ = parse_coordinate(row.get("lat"))
                lon, _ = parse_coordinate(row.get("lon"))
                fast_delivery, _ = parse_nullable_bool(row.get("supports_fast_delivery"))
                objects.append(Shop(
                    source_id=source_id,
                    name=parse_nullable_text(row.get("name")) or "",
                    category_names=category_names,
                    address=parse_nullable_text(row.get("address")),
                    location_label=parse_nullable_text(row.get("location_label")),
                    lat=lat if lat is None or -90 <= lat <= 90 else None,
                    lon=lon if lon is None or -180 <= lon <= 180 else None,
                    contacts=contacts,
                    payment_options=payment_options,
                    accepts_in_person_credit=has_in_person_credit(payment_options),
                    weekly_hours=weekly_hours,
                    website_url=parse_nullable_text(row.get("website_url")),
                    instagram=parse_nullable_text(row.get("instagram")),
                    supports_fast_delivery=fast_delivery,
                ))
            created, changed = self._upsert_batch(Shop, objects, update_fields, batch_size)
            inserted += created
            updated += changed
        return {"shops_inserted": inserted, "shops_updated": updated}

    def _import_offers(
        self, reader, batch_size: int, product_ids: set[str], shop_ids: set[str],
        allow_orphans: bool,
    ):
        inserted = updated = skipped = 0
        update_fields = [
            "product", "shop", "price_toman", "last_price_changed_at", "seller_title",
            "description", "warranty",
        ]
        for rows in self._batches(reader, "offers.csv", batch_size):
            objects = []
            for row in rows:
                source_id = parse_nullable_text(row.get("offer_id"))
                product_id = parse_nullable_text(row.get("product_id"))
                shop_id = parse_nullable_text(row.get("shop_id"))
                if not source_id or not product_id or not shop_id:
                    skipped += 1
                    continue
                if product_id not in product_ids or shop_id not in shop_ids:
                    if allow_orphans:
                        skipped += 1
                        continue
                    raise CommandError(
                        f"Unexpected orphan offer {source_id}; preflight and import inputs differ."
                    )
                price, _ = parse_decimal_price(row.get("price_toman"))
                changed_at, _ = parse_timestamp(row.get("last_price_changed_at"))
                warranty, _ = parse_json_cell(row.get("warranty"), dict, None)
                objects.append(Offer(
                    source_id=source_id,
                    product_id=product_id,
                    shop_id=shop_id,
                    price_toman=price,
                    last_price_changed_at=changed_at,
                    seller_title=parse_nullable_text(row.get("seller_title")),
                    description=parse_nullable_text(row.get("description")),
                    warranty=warranty,
                ))
            created, changed = self._upsert_batch(Offer, objects, update_fields, batch_size)
            inserted += created
            updated += changed
        return {
            "offers_inserted": inserted,
            "offers_updated": updated,
            "offers_skipped_orphan": skipped,
        }
