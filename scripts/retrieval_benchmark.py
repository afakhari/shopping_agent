#!/usr/bin/env python3
"""Generate 50 UNJUDGED catalogue query seeds; probe real HTTP without fake gold metrics."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import time
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from predeploy_smoke import validate_base_url


def _csv_rows(archive: zipfile.ZipFile, name: str):
    with archive.open(name) as source:
        yield from csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig"))


def _present(text: object) -> bool:
    return isinstance(text, str) and text.strip() not in {"", "null", "None"}


def make_seeds(zip_path: Path) -> dict:
    """Sample distinct catalogue strata; a seed ID is NOT a judged relevant label."""
    with zipfile.ZipFile(zip_path) as archive:
        eligible_ids = {row["product_id"] for row in _csv_rows(archive, "offers.csv")}
        products = [
            row for row in _csv_rows(archive, "products.csv")
            if row["product_id"] in eligible_ids and _present(row.get("persian_title"))
        ]

    categories = Counter(row["category_name"] for row in products
                         if _present(row.get("category_name")))
    by_category = {}
    brand_category = {}
    models = []
    titles = []
    for row in products:
        category, brand = row.get("category_name", ""), row.get("brand_name", "")
        if _present(category):
            by_category.setdefault(category, row)
        if _present(brand) and _present(category):
            brand_category.setdefault(brand, row)
        if _present(row.get("model")):
            models.append(row)
        if 18 <= len(row["persian_title"]) <= 115:
            titles.append(row)

    cases = []
    used_ids = set()

    def add(query: str, kind: str, row: dict, filters: dict | None = None):
        text = " ".join(query.split()).strip()
        if not text or len(text) > 190:
            return False
        case = {
            "id": f"Q{len(cases) + 1:02d}",
            "query": text,
            "stratum": kind,
            "seed_product_id": row["product_id"],
            "hard_filters": filters or {},
            "label_status": "unjudged",
        }
        cases.append(case)
        used_ids.add(row["product_id"])
        return True

    for category, _ in sorted(categories.items(), key=lambda item: (-item[1], item[0]))[:15]:
        add(category, "category", by_category[category])
    for row in sorted(titles, key=lambda row: (row["category_name"], row["product_id"])):
        if len(cases) >= 30:
            break
        if row["product_id"] not in used_ids:
            add(row["persian_title"], "title", row)
    for brand, row in sorted(brand_category.items(), key=lambda item: item[0]):
        if len(cases) >= 40:
            break
        if row["product_id"] not in used_ids:
            add(f"{brand} {row['category_name']}", "brand_category", row)
    for row in sorted(models, key=lambda item: item["product_id"]):
        if len(cases) >= 45:
            break
        if row["product_id"] not in used_ids:
            prefix = row["brand_name"] if _present(row.get("brand_name")) else row["category_name"]
            add(f"{prefix} {row['model']}", "model", row)

    # Five requirement-focused probes. They are sanity checks, not gold judgments.
    exemplar = by_category.get("هدفون") or (products[0] if products else None)
    if not exemplar or len(cases) != 45:
        raise ValueError("Dataset does not provide all 45 distinct category/title/brand/model seeds")
    add("هدفون", "budget", exemplar, {"max_price_toman": "3000000"})
    add("هدفون", "credit", exemplar, {"must_have_in_person_credit": "true"})
    add("فشارسنج", "ambiguous", by_category.get("فشارسنج پزشکی") or exemplar)
    add("هدفون", "budget_strict", exemplar, {"max_price_toman": "1"})
    add("هدفون", "sort", exemplar, {"sort": "price_asc"})

    if len(cases) != 50:
        raise ValueError(f"Expected exactly 50 unjudged seeds, got {len(cases)}")
    digest = hashlib.sha256()
    with zip_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "status": "unverified_seed_not_human_gold",
        "source_zip_sha256": digest.hexdigest(),
        "source_product_count": len(products),
        "query_count": len(cases),
        "warning": "seed_product_id is not a judged relevance label; no Recall/MRR may be claimed",
        "queries": cases,
    }


def hard_filter_errors(case: dict, results: list[dict]) -> list[str]:
    errors = []
    constraints = case.get("hard_filters") or {}
    budget = constraints.get("max_price_toman")
    credit = str(constraints.get("must_have_in_person_credit", "false")).lower() == "true"
    radius = constraints.get("radius_m")
    for item in results:
        offer = item.get("best_offer", {})
        if not offer.get("id") or not offer.get("shop", {}).get("id"):
            errors.append("missing registered offer/shop")
        if budget is not None:
            price = offer.get("price_toman")
            if price is None or int(price) > int(budget):
                errors.append("budget violation")
        if credit and offer.get("in_person_credit_eligible") is not True:
            errors.append("in-person credit violation")
        if radius is not None:
            distance = offer.get("shop", {}).get("distance_m")
            if distance is None or distance > int(radius):
                errors.append("location radius violation")
    return errors


def probe(base: str, seed: dict, timeout: float = 15.0) -> dict:
    rows = []
    for case in seed["queries"]:
        query_params = {"q": case["query"], "page_size": 10, **case.get("hard_filters", {})}
        url = base.rstrip("/") + "/api/v1/catalog/search/?" + urlencode(query_params)
        started = time.perf_counter()
        try:
            with urlopen(url, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                body = json.loads(response.read(2_000_000))
            items = body.get("results", [])
            issues = hard_filter_errors(case, items)
            rows.append({
                "id": case["id"], "stratum": case["stratum"],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "seed_hit_at10": any(
                    item.get("product", {}).get("id") == case["seed_product_id"] for item in items
                ),
                "result_count": body.get("total"),
                "hard_filter_violations": issues,
                "error": None,
            })
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            rows.append({"id": case["id"], "error": type(exc).__name__,
                         "hard_filter_violations": ["request failed"]})
    measured = [x["latency_ms"] for x in rows if "latency_ms" in x]
    violations = sum(len(x["hard_filter_violations"]) for x in rows)
    return {
        "status": "unjudged_probe_not_gold_evaluation",
        "source_zip_sha256": seed.get("source_zip_sha256"),
        "metrics": {
            "queries_executed": len(rows), "requests_succeeded": len(measured),
            "seed_hits_at10_not_recall": sum(bool(r.get("seed_hit_at10")) for r in rows),
            "single_run_p95_ms": (
                sorted(measured)[max(0, math.ceil(.95 * len(measured)) - 1)] if measured else None
            ),
            "median_ms": round(statistics.median(measured), 2) if measured else None,
            "hard_filter_violations": violations,
            "Recall@10": "NOT_MEASURED_NO_GOLD",
            "MRR@10": "NOT_MEASURED_NO_GOLD",
        },
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    seed = sub.add_parser("seed")
    seed.add_argument("--zip", required=True, type=Path)
    seed.add_argument("--output", required=True, type=Path)
    check = sub.add_parser("probe")
    check.add_argument("--seed", required=True, type=Path)
    check.add_argument("--base-url", required=True)
    check.add_argument("--output", required=True, type=Path)
    check.add_argument("--allow-http-local", action="store_true")
    args = parser.parse_args()
    if args.mode == "seed":
        output = make_seeds(args.zip)
    else:
        base = validate_base_url(args.base_url, args.allow_http_local)
        seed_data = json.loads(args.seed.read_text(encoding="utf-8"))
        if seed_data.get("status") != "unverified_seed_not_human_gold":
            raise ValueError("Only explicit unjudged seed files can be used by this probe")
        output = probe(base, seed_data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"{args.mode.upper()}_RESULT={output.get('metrics', {}).get('hard_filter_violations', 'UNJUDGED')} "
          f"written={args.output}")
    if args.mode == "probe" and output["metrics"]["hard_filter_violations"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
