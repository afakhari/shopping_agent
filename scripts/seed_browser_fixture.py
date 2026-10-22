"""Populate an isolated CI database with synthetic shops and products.

Do not use or upload the Torob competition CSV/ZIP in public GitHub CI.
Run after Django migrations with DATABASE_URL pointing at a disposable database.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from apps.catalog.models import Offer, Product, Shop  # noqa: E402
from apps.catalog.services.normalization import normalize_persian_text  # noqa: E402


def main() -> None:
    product_name = "هدفون بی سیم تست مرورگر"
    with transaction.atomic():
        product, _ = Product.objects.update_or_create(
            source_id="browser-product-headset",
            defaults={
                "persian_title": product_name,
                "normalized_title": normalize_persian_text(product_name),
                "category_name": "هدفون",
                "brand_name": "برند آزمایشی",
                "specs": [
                    {"key": "نوع اتصال", "section": "صدا", "value": "بی سیم"},
                    {"key": "مدت شارژ", "section": "صدا", "value": "۱۰ ساعت"},
                ],
            },
        )
        sellers = (
            ("browser-shop-a", "فروشگاه آزمایشی الف", "تهران، پاساژ نمونه، طبقه دوم، واحد ۱۲",
             35.7001, 51.4001, 750000),
            ("browser-shop-b", "فروشگاه آزمایشی ب", "تهران، پاساژ نمونه، طبقه اول، واحد ۳",
             35.7010, 51.4010, 800000),
        )
        for shop_id, name, address, lat, lon, price in sellers:
            shop, _ = Shop.objects.update_or_create(
                source_id=shop_id,
                defaults={
                    "name": name, "address": address, "lat": lat, "lon": lon,
                    "location_label": "مرکز تهران", "payment_options": [],
                    "weekly_hours": {"sat": {"status": "declared", "shifts": [
                        {"start_time": "09:00:00", "end_time": "20:00:00"},
                    ]}},
                },
            )
            Offer.objects.update_or_create(
                source_id=f"browser-offer-{shop_id}",
                defaults={
                    "shop": shop, "product": product,
                    "price_toman": Decimal(price),
                    "seller_title": f"هدفون آزمایشی در {name}",
                    "warranty": {"provider": "گارانتی آزمایشی", "period_months": 12},
                },
            )
        comparison_name = "هدفون بی سیم تست مرورگر مدل دوم"
        comparison_product, _ = Product.objects.update_or_create(
            source_id="browser-product-headset-comparison",
            defaults={
                "persian_title": comparison_name,
                "normalized_title": normalize_persian_text(comparison_name),
                "category_name": "هدفون",
                "brand_name": "برند آزمایشی",
                "specs": [
                    {"key": "نوع اتصال", "section": "صدا", "value": "بی سیم"},
                    {"key": "مدت شارژ", "section": "صدا", "value": "۶ ساعت"},
                ],
            },
        )
        Offer.objects.update_or_create(
            source_id="browser-offer-comparison",
            defaults={
                "shop": Shop.objects.get(pk="browser-shop-b"),
                "product": comparison_product,
                "price_toman": Decimal("1250000"),
                "seller_title": "هدفون آزمایشی مدل دوم",
                "warranty": {"provider": "گارانتی آزمایشی", "period_months": 6},
            },
        )
    print("Synthetic browser test catalog seeded; no competition data copied.")


if __name__ == "__main__":
    main()
