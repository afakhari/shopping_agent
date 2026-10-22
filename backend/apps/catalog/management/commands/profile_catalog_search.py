"""Safe, read-only PostgreSQL search profiler with bounded query runtime.

The objective is to distinguish expensive text matching, offer filtering,
and the full ranked catalog query; never runs the BoxAPI model or exports
customer/product records. It is safe on a populated local challenge dataset.
"""
from __future__ import annotations

import json
import time

from django.core.management.base import BaseCommand
from django.db import DatabaseError, connection, transaction
from django.db.models import Exists, OuterRef

from apps.catalog.models import Product
from apps.catalog.services.normalization import normalize_persian_text
from apps.search.serializers import ProductSearchSerializer
from apps.search.services import _product_match_query, eligible_offers, product_search_page


class Command(BaseCommand):
    help = "Time catalog search stages under a statement timeout, without calling BoxAPI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--query", default="هدفون",
            help="Persian search query; default is a built-in UTF-8 literal to avoid Windows ANSI issues",
        )
        parser.add_argument(
            "--timeout-ms", type=int, default=8000,
            help="Maximum SQL runtime per stage in milliseconds (1000..30000)",
        )

    def handle(self, *args, **options):
        normalized = normalize_persian_text(options["query"])
        timeout_ms = max(1000, min(30000, options["timeout_ms"]))
        payload = ProductSearchSerializer(data={"q": options["query"], "page_size": 1})
        payload.is_valid(raise_exception=True)
        filters = payload.validated_data

        matched = Product.objects.filter(_product_match_query(normalized))
        eligible = eligible_offers(filters).order_by()
        matched_eligible = matched.filter(
            Exists(eligible.filter(product_id=OuterRef("source_id")))
        )

        def limited(operation):
            start = time.perf_counter()
            try:
                with transaction.atomic():
                    if connection.vendor == "postgresql":
                        with connection.cursor() as cursor:
                            cursor.execute("SET LOCAL statement_timeout = %s", [timeout_ms])
                    value = operation()
                return {"status": "ok", "elapsed_ms": round((time.perf_counter() - start)*1000, 1), "value": value}
            except DatabaseError as exc:
                return {"status": type(exc).__name__, "elapsed_ms": round((time.perf_counter()-start)*1000, 1)}
        result = {
            "database": connection.vendor,
            "query": options["query"],
            "timeout_ms_per_stage": timeout_ms,
            "stages": {},
        }
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT c.relname, i.indisvalid FROM pg_index i "
                    "JOIN pg_class c ON c.oid=i.indexrelid "
                    "JOIN pg_class t ON t.oid=i.indrelid "
                    "WHERE t.relname = 'catalog_product' "
                    "AND (c.relname LIKE '%trgm%' OR c.relname LIKE '%title%') "
                    "ORDER BY c.relname"
                )
                result["product_indexes"] = [
                    {"name": name, "valid": valid} for name, valid in cursor.fetchall()
                ]
        result["stages"]["text_candidate_count"] = limited(matched.count)
        result["stages"]["eligible_product_count"] = limited(matched_eligible.count)
        result["stages"]["full_search_page_size_1"] = limited(
            lambda: {
                "total": (value := product_search_page(filters))["total"],
                "returned": len(value["results"]),
            }
        )
        if connection.vendor == "postgresql":
            def plan():
                parsed = json.loads(matched_eligible.explain(format="JSON"))
                nodes = []
                def visit(node):
                    if not isinstance(node, dict):
                        return
                    nodes.append({
                        "type": node.get("Node Type"),
                        "index": node.get("Index Name"),
                        "relation": node.get("Relation Name"),
                    })
                    for child in node.get("Plans", []):
                        visit(child)
                visit(parsed[0]["Plan"])
                return nodes[:35]
            result["query_plan_nodes"] = limited(plan)
        self.stdout.write(json.dumps(result, ensure_ascii=True, indent=2))
