#!/usr/bin/env python3
"""Stream and audit the challenge dataset using only Python's standard library.

The script never prints raw contact values or entire records. It can read the original ZIP
or a directory containing products.csv, shops.csv, and offers.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, TextIO

FILES = ("products.csv", "shops.csv", "offers.csv")
JSON_FIELDS = {
    "products.csv": {"image_urls": list, "specs": list},
    "shops.csv": {
        "category_names": list, "contacts": list, "payment_options": list, "weekly_hours": dict
    },
    "offers.csv": {"warranty": dict},
}
ID_COLUMN = {"products.csv": "product_id", "shops.csv": "shop_id", "offers.csv": "offer_id"}


def open_csv(source: Path, name: str) -> TextIO:
    """Open a CSV from an archive or directory. Caller must close the returned text stream."""
    if source.is_dir():
        path = source / name
        if not path.is_file():
            raise FileNotFoundError(path)
        return path.open("r", encoding="utf-8-sig", newline="")
    raise RuntimeError("Use open_source_csv() for archive support")


def open_source_csv(source: Path, name: str, archive: zipfile.ZipFile | None) -> TextIO:
    if archive is not None:
        try:
            raw = archive.open(name)
        except KeyError as exc:
            raise FileNotFoundError(f"'{name}' not found in {source}") from exc
        import io
        return io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
    return open_csv(source, name)


def is_null(value: str | None) -> bool:
    return value is None or not value.strip() or value.strip().casefold() == "null"


def parse_json(value: str | None, expected: type) -> tuple[Any, bool, bool]:
    """Return (value, invalid, absent)."""
    if is_null(value):
        return None, False, True
    try:
        parsed = json.loads(value or "")
    except (json.JSONDecodeError, TypeError):
        return None, True, False
    if parsed is None:
        return None, False, True
    if not isinstance(parsed, expected):
        return None, True, False
    return parsed, False, False


def parse_number(value: str | None) -> Decimal | None:
    if is_null(value):
        return None
    try:
        number = Decimal((value or "").strip())
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: str | None) -> datetime | None:
    if is_null(value):
        return None
    try:
        result = datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def field_stats(source: Path, name: str, archive: zipfile.ZipFile | None) -> tuple[dict[str, Any], set[str]]:
    summary: dict[str, Any] = {
        "rows": 0, "duplicate_ids": 0, "missing_ids": 0, "null_by_column": {},
        "json_invalid_by_column": {}, "headers": [],
    }
    seen_ids: set[str] = set()
    with open_source_csv(source, name, archive) as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if not headers:
            raise ValueError(f"{name}: missing CSV header")
        summary["headers"] = headers
        id_col = ID_COLUMN[name]
        if id_col not in headers:
            raise ValueError(f"{name}: required ID column {id_col!r} missing")
        for column in headers:
            summary["null_by_column"][column] = 0
        for column in JSON_FIELDS.get(name, {}):
            summary["json_invalid_by_column"][column] = 0
        for row in reader:
            summary["rows"] += 1
            row_id = (row.get(id_col) or "").strip()
            if not row_id or row_id.casefold() == "null":
                summary["missing_ids"] += 1
            elif row_id in seen_ids:
                summary["duplicate_ids"] += 1
            else:
                seen_ids.add(row_id)
            for column in headers:
                if is_null(row.get(column)):
                    summary["null_by_column"][column] += 1
            for column, expected in JSON_FIELDS.get(name, {}).items():
                _, invalid, _ = parse_json(row.get(column), expected)
                summary["json_invalid_by_column"][column] += int(invalid)
    summary["unique_ids"] = len(seen_ids)
    return summary, seen_ids


def audit(source: Path, max_price: Decimal) -> dict[str, Any]:
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_file() and not zipfile.is_zipfile(source):
        raise ValueError(f"Expected a ZIP archive or directory: {source}")
    archive = zipfile.ZipFile(source) if source.is_file() else None
    try:
        report: dict[str, Any] = {
            "source": source.name,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "thresholds": {"max_reasonable_price_toman": str(max_price)},
            "tables": {},
            "relations": {},
            "quality": {},
        }
        ids_by_table: dict[str, set[str]] = {}
        for name in FILES:
            stats, ids = field_stats(source, name, archive)
            report["tables"][name] = stats
            ids_by_table[name] = ids

        product_summary: dict[str, Any] = {
            "nonempty_titles": 0, "nonempty_brands": 0, "nonempty_categories": 0,
            "nonempty_models": 0, "products_with_images": 0, "products_with_specs": 0,
            "image_urls_total": 0, "specs_total": 0,
        }
        with open_source_csv(source, "products.csv", archive) as stream:
            for row in csv.DictReader(stream):
                product_summary["nonempty_titles"] += int(not is_null(row.get("persian_title")))
                product_summary["nonempty_brands"] += int(not is_null(row.get("brand_name")))
                product_summary["nonempty_categories"] += int(not is_null(row.get("category_name")))
                product_summary["nonempty_models"] += int(not is_null(row.get("model")))
                image_urls, _, _ = parse_json(row.get("image_urls"), list)
                specs, _, _ = parse_json(row.get("specs"), list)
                image_count = len(image_urls) if isinstance(image_urls, list) else 0
                specs_count = len(specs) if isinstance(specs, list) else 0
                product_summary["image_urls_total"] += image_count
                product_summary["specs_total"] += specs_count
                product_summary["products_with_images"] += int(image_count > 0)
                product_summary["products_with_specs"] += int(specs_count > 0)
        report["product_profile"] = product_summary

        shops_summary: dict[str, Any] = {
            "with_name": 0, "with_address": 0, "with_coordinates": 0,
            "with_website": 0, "with_instagram": 0, "with_image_not_applicable": None,
            "with_pasazh_hint": 0, "with_floor_hint": 0, "with_unit_hint": 0,
            "with_weekly_hours": 0, "with_contact_channel": 0,
            "unique_shops_with_in_person_credit": 0,
            "payment_option_entries_by_channel": {}, "category_values": Counter(),
            "lat_out_of_range": 0, "lon_out_of_range": 0,
        }
        eligible_credit_shops: set[str] = set()
        with open_source_csv(source, "shops.csv", archive) as stream:
            for row in csv.DictReader(stream):
                shop_id = (row.get("shop_id") or "").strip()
                shops_summary["with_name"] += int(not is_null(row.get("name")))
                shops_summary["with_address"] += int(not is_null(row.get("address")))
                lat, lon = parse_number(row.get("lat")), parse_number(row.get("lon"))
                has_coords = lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180
                shops_summary["with_coordinates"] += int(has_coords)
                shops_summary["lat_out_of_range"] += int(lat is not None and not (-90 <= lat <= 90))
                shops_summary["lon_out_of_range"] += int(lon is not None and not (-180 <= lon <= 180))
                shops_summary["with_website"] += int(not is_null(row.get("website_url")))
                shops_summary["with_instagram"] += int(not is_null(row.get("instagram")))
                address = (row.get("address") or "").casefold()
                shops_summary["with_pasazh_hint"] += int("پاساژ" in address or "مجتمع" in address or "مال " in address)
                shops_summary["with_floor_hint"] += int(any(s in address for s in ("طبقه", "همکف", "زیرزمین", "طبقه‌ی")))
                shops_summary["with_unit_hint"] += int(any(s in address for s in ("واحد", "پلاک", "مغازه شماره", "شماره واحد")))
                hours, _, hours_absent = parse_json(row.get("weekly_hours"), dict)
                shops_summary["with_weekly_hours"] += int(bool(hours) and not hours_absent)
                contacts, _, _ = parse_json(row.get("contacts"), list)
                shops_summary["with_contact_channel"] += int(bool(contacts))
                payments, _, _ = parse_json(row.get("payment_options"), list)
                has_credit = False
                if isinstance(payments, list):
                    for item in payments:
                        if not isinstance(item, dict):
                            continue
                        ch = str(item.get("channel") or "unknown")
                        channels = shops_summary["payment_option_entries_by_channel"]
                        channels[ch] = channels.get(ch, 0) + 1
                        if ch == "in_person":
                            has_credit = True
                if has_credit and shop_id:
                    eligible_credit_shops.add(shop_id)
        shops_summary["unique_shops_with_in_person_credit"] = len(eligible_credit_shops)
        report["shop_profile"] = shops_summary

        offers_summary: dict[str, Any] = {
            "valid_prices": 0, "null_prices": 0, "non_positive_prices": 0,
            "over_threshold_prices": 0, "invalid_price_values": 0,
            "orphan_product_refs": 0, "orphan_shop_refs": 0,
            "timestamps_valid": 0, "timestamps_invalid": 0, "timestamps_missing": 0,
            "oldest_price_change_utc": None, "newest_price_change_utc": None,
            "median_price_age_days_at_audit": None,
        }
        price_ages: list[float] = []
        dates: list[datetime] = []
        with open_source_csv(source, "offers.csv", archive) as stream:
            for row in csv.DictReader(stream):
                amount_raw = row.get("price_toman")
                amount = parse_number(amount_raw)
                if is_null(amount_raw):
                    offers_summary["null_prices"] += 1
                elif amount is None:
                    offers_summary["invalid_price_values"] += 1
                else:
                    offers_summary["valid_prices"] += 1
                    if amount <= 0:
                        offers_summary["non_positive_prices"] += 1
                    if amount > max_price:
                        offers_summary["over_threshold_prices"] += 1
                if (row.get("product_id") or "").strip() not in ids_by_table["products.csv"]:
                    offers_summary["orphan_product_refs"] += 1
                if (row.get("shop_id") or "").strip() not in ids_by_table["shops.csv"]:
                    offers_summary["orphan_shop_refs"] += 1
                raw_date = row.get("last_price_changed_at")
                dt = parse_date(raw_date)
                if is_null(raw_date):
                    offers_summary["timestamps_missing"] += 1
                elif dt is None:
                    offers_summary["timestamps_invalid"] += 1
                else:
                    offers_summary["timestamps_valid"] += 1
                    dates.append(dt)
                    price_ages.append((datetime.now(timezone.utc) - dt).total_seconds() / 86400)
        if dates:
            offers_summary["oldest_price_change_utc"] = min(dates).isoformat()
            offers_summary["newest_price_change_utc"] = max(dates).isoformat()
            offers_summary["median_price_age_days_at_audit"] = round(statistics.median(price_ages), 2)
        report["offer_profile"] = offers_summary
        report["relations"] = {
            "offers_missing_product": offers_summary["orphan_product_refs"],
            "offers_missing_shop": offers_summary["orphan_shop_refs"],
            "products_without_offer": len(ids_by_table["products.csv"] - _offered_product_ids(source, archive)),
        }

        for name, stats in report["tables"].items():
            report["quality"][name] = {
                "rows": stats["rows"], "unique_ids": stats["unique_ids"],
                "duplicate_ids": stats["duplicate_ids"], "missing_ids": stats["missing_ids"],
                "invalid_json_cells": sum(stats["json_invalid_by_column"].values()),
            }
        return report
    finally:
        if archive is not None:
            archive.close()


def _offered_product_ids(source: Path, archive: zipfile.ZipFile | None) -> set[str]:
    ids: set[str] = set()
    with open_source_csv(source, "offers.csv", archive) as stream:
        for row in csv.DictReader(stream):
            pid = (row.get("product_id") or "").strip()
            if pid:
                ids.add(pid)
    return ids


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dataset audit report (automatically generated)", "",
        f"- Source: `{report['source']}`",
        f"- Generated at: `{report['generated_at_utc']}`",
        f"- Price outlier threshold (Toman): `{report['thresholds']['max_reasonable_price_toman']}`",
        "", "## Table counts", "", "| File | Rows | Unique IDs | Duplicate IDs | Missing IDs | Invalid JSON cells |", "|---|---:|---:|---:|---:|---:|",
    ]
    for name, stats in report["tables"].items():
        invalid_json = sum(stats["json_invalid_by_column"].values())
        lines.append(f"| `{name}` | {stats['rows']:,} | {stats['unique_ids']:,} | {stats['duplicate_ids']:,} | {stats['missing_ids']:,} | {invalid_json:,} |")
    lines += ["", "## Missing-value coverage", ""]
    for name, stats in report["tables"].items():
        lines += [f"### `{name}`", "", "| Column | Missing or null-like | Share |", "|---|---:|---:|"]
        for column, count in sorted(stats["null_by_column"].items(), key=lambda item: item[1], reverse=True):
            share = (count / stats["rows"] * 100) if stats["rows"] else 0
            lines.append(f"| `{column}` | {count:,} | {share:.2f}% |")
        lines.append("")
    lines += ["## Product profile", "", "| Metric | Count |", "|---|---:|"]
    for key, value in report["product_profile"].items():
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "## Shop profile", "", "| Metric | Count |", "|---|---:|"]
    for key, value in report["shop_profile"].items():
        if isinstance(value, int):
            lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "### Payment option entries by channel", "", "| Channel | Entries |", "|---|---:|"]
    for channel, count in sorted(report["shop_profile"]["payment_option_entries_by_channel"].items()):
        lines.append(f"| `{channel}` | {count:,} |")
    lines += ["", "## Offers", "", "| Metric | Value |", "|---|---:|"]
    for key, value in report["offer_profile"].items():
        lines.append(f"| `{key}` | {value} |")
    lines += ["", "## Relationships", "", "| Metric | Value |", "|---|---:|"]
    for key, value in report["relations"].items():
        lines.append(f"| `{key}` | {value:,} |")
    lines += ["", "> This report does not expose phone numbers or full source records. Counts describe the provided snapshot only; offers and contacts are not proof of live inventory or reachability.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Dataset ZIP path or directory containing CSV files")
    parser.add_argument("--report-dir", type=Path, default=Path("reports"), help="Output directory")
    parser.add_argument("--max-price-toman", default="100000000000", help="Outlier threshold; does not modify source data")
    args = parser.parse_args(argv)
    try:
        max_price = Decimal(args.max_price_toman)
        if not max_price.is_finite() or max_price <= 0:
            raise ValueError("--max-price-toman must be a positive finite decimal")
        report = audit(args.source, max_price)
        args.report_dir.mkdir(parents=True, exist_ok=True)
        json_path = args.report_dir / "dataset-audit.json"
        md_path = args.report_dir / "dataset-audit.md"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(render_markdown(report), encoding="utf-8")
        print(f"Audit complete: {json_path} and {md_path}")
        for name, stats in report["tables"].items():
            print(f"{name}: rows={stats['rows']:,}, unique_ids={stats['unique_ids']:,}, duplicate_ids={stats['duplicate_ids']:,}, missing_ids={stats['missing_ids']:,}")
        print(f"Orphan product refs: {report['relations']['offers_missing_product']:,}")
        print(f"Orphan shop refs: {report['relations']['offers_missing_shop']:,}")
        print(f"Shops with in-person credit entries: {report['shop_profile']['unique_shops_with_in_person_credit']:,}")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"Dataset audit failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
