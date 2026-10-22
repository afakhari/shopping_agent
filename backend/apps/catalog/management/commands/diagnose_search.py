"""Read-only diagnostics for the real catalog search path (never dumps raw records)."""
from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.test import Client

from apps.catalog.models import Offer, Product
from apps.catalog.services.normalization import normalize_persian_text


class Command(BaseCommand):
    help = "Diagnose whether real product rows and API search results agree."

    def add_arguments(self, parser):
        parser.add_argument("--query", type=str, default="هدفون")

    def handle(self, *args, **options):
        query = options["query"]
        normalized = normalize_persian_text(query)
        candidates = Product.objects.filter(
            Q(normalized_title__icontains=normalized)
            | Q(category_name__icontains=normalized)
        )
        eligible_offer_count = Offer.objects.filter(
            product__in=candidates.values("source_id"),
        ).filter(
            Q(price_toman__isnull=True)
            | Q(price_toman__range=(1, settings.MAX_REASONABLE_PRICE_TOMAN))
        ).count()

        summary = {
            "query": query,
            "normalized_query": normalized,
            "db": {
                "products": Product.objects.count(),
                "offers": Offer.objects.count(),
                "products_matching_title_or_category": candidates.count(),
                "products_with_normalized_title": Product.objects.exclude(
                    normalized_title=""
                ).count(),
                "eligible_matching_offers": eligible_offer_count,
            },
        }

        try:
            response = Client(HTTP_HOST="localhost").get(
                "/api/v1/catalog/search/",
                {"q": query, "page": "1", "page_size": "2"},
            )
            summary["django_api"] = {"status_code": response.status_code}
            if response.status_code == 200:
                payload = response.json()
                summary["django_api"]["total"] = payload.get("total")
                summary["django_api"]["query"] = payload.get("query")
                summary["django_api"]["returned_results"] = len(
                    payload.get("results", [])
                )
            else:
                summary["django_api"]["body_preview"] = (
                    response.content.decode("utf-8", errors="replace")[:300]
                )
        except Exception as exc:
            summary["django_api"] = {
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            }

        self.stdout.write(json.dumps(summary, ensure_ascii=True, indent=2))
