"""Read-only database verification after importing the Torob challenge dataset."""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.catalog.models import Offer, Product, Shop


class Command(BaseCommand):
    help = "Verify imported Product/Shop/Offer counts and basic relational integrity."

    def add_arguments(self, parser):
        parser.add_argument("--products", type=int, default=None, help="Expected product count")
        parser.add_argument("--shops", type=int, default=None, help="Expected shop count")
        parser.add_argument("--offers", type=int, default=None, help="Expected offer count")
        parser.add_argument("--json", action="store_true", help="Print a machine-readable summary")
        parser.add_argument("--sample-product", type=str, default=None)
        parser.add_argument("--sample-shop", type=str, default=None)
        parser.add_argument("--sample-offer", type=str, default=None)

    def handle(self, *args, **options):
        expected = {
            "products": options["products"],
            "shops": options["shops"],
            "offers": options["offers"],
        }
        if any(value is not None and value <= 0 for value in expected.values()):
            raise CommandError("Expected counts must be positive integers.")

        try:
            actual = {
                "products": Product.objects.count(),
                "shops": Shop.objects.count(),
                "offers": Offer.objects.count(),
            }
            priced_offer_exists = Offer.objects.filter(price_toman__isnull=False).exists()
            related_offer_exists = Offer.objects.filter(
                product__isnull=False, shop__isnull=False
            ).exists()
        except DatabaseError as exc:
            raise CommandError("Dataset tables are unavailable; run migrations first.") from exc

        errors = [f"{name}: table is empty" for name, count in actual.items() if count == 0]
        errors.extend(
            f"{name}: expected {value:,}, found {actual[name]:,}"
            for name, value in expected.items()
            if value is not None and actual[name] != value
        )
        for label, model, source_id in (
            ("product", Product, options["sample_product"]),
            ("shop", Shop, options["sample_shop"]),
            ("offer", Offer, options["sample_offer"]),
        ):
            if source_id and not model.objects.filter(source_id=source_id).exists():
                errors.append(f"sample {label} missing: {source_id}")
        if actual["offers"] and not priced_offer_exists:
            errors.append("All offers are missing prices")
        if actual["offers"] and not related_offer_exists:
            errors.append("No offer resolves to a product and shop")

        summary = {"status": "ok" if not errors else "mismatch", "counts": actual}
        if options["json"]:
            self.stdout.write(json.dumps(summary, ensure_ascii=False))
        else:
            self.stdout.write("\n".join(f"{key}: {val:,}" for key, val in actual.items()))
        if errors:
            raise CommandError("Dataset verification failed: " + "; ".join(errors))
        if not options["json"]:
            self.stdout.write(self.style.SUCCESS("Dataset counts and sample relationships verified."))
