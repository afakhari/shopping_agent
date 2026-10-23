"""Evidence-only comparison for two or three selected physical-shopping products.

All rows must have an eligible registered Offer. Absent specifications are explicitly
unknown. Never turn registered shop data into a claim of live stock.
"""
from __future__ import annotations

from typing import Any

from apps.catalog.models import Product
from apps.search.services import eligible_offer_list


def build_evidence_comparison(product_ids: list[str], filters: dict[str, Any]) -> dict[str, Any] | None:
    """Produce the existing GenUI comparison_table contract, or fail closed."""
    if not 2 <= len(product_ids) <= 3 or len(set(product_ids)) != len(product_ids):
        return None
    products = {p.source_id: p for p in Product.objects.filter(source_id__in=product_ids)}
    if len(products) != len(product_ids):
        return None

    candidates: list[tuple[Product, object, dict[str, str]]] = []
    for pid in product_ids:
        product = products[pid]
        offer = eligible_offer_list(filters, product_id=pid).select_related("shop").first()
        if offer is None:
            return None
        specs: dict[str, str] = {}
        for raw in product.specs if isinstance(product.specs, list) else []:
            if not isinstance(raw, dict):
                continue
            key, value = raw.get("key"), raw.get("value")
            if (isinstance(key, str) and isinstance(value, str)
                and 0 < len(key.strip()) <= 75 and 0 < len(value.strip()) <= 220
                and key.strip() not in {"نام محصول", "عنوان محصول", "کد محصول"}):
                specs.setdefault(key.strip(), value.strip())
        candidates.append((product, offer, specs))

    shared = set.intersection(*(set(specs) for _, _, specs in candidates))
    differing = [key for key in shared if len({specs[key] for _, _, specs in candidates}) > 1]
    selected_keys = sorted(differing)[:5]
    columns = [
        {"key": "product", "label": "محصول"},
        {"key": "price", "label": "قیمت ثبت‌شده"},
        {"key": "brand", "label": "برند ثبت‌شده"},
        {"key": "model", "label": "مدل ثبت‌شده"},
        {"key": "shop", "label": "فروشگاه دارای آفر"},
        {"key": "credit", "label": "اعتبار حضوری"},
        {"key": "updated", "label": "زمان تغییر قیمت"},
        *[{"key": f"spec_{index}", "label": key} for index, key in enumerate(selected_keys)],
    ]
    rows = []
    for product, offer, specs in candidates:
        row = {
            "id": product.source_id,
            "product": product.persian_title or product.source_id,
            "price": f"{offer.price_toman:,.0f} تومان" if offer.price_toman is not None else "ثبت نشده",
            "brand": product.brand_name or "ثبت نشده",
            "model": product.model or "ثبت نشده",
            "shop": offer.shop.name or "نامشخص",
            "credit": "برای این آفر ثبت‌شده" if getattr(offer, "in_person_credit_eligible", False) else "برای این آفر ثبت نشده",
            "updated": offer.last_price_changed_at.isoformat() if offer.last_price_changed_at else "ثبت نشده",
        }
        for index, key in enumerate(selected_keys):
            row[f"spec_{index}"] = specs[key]
        rows.append(row)
    return {
        "title": "مقایسه بر اساس مشخصات و آفرهای ثبت‌شده",
        "columns": columns,
        "rows": rows,
        "source_type": "registered_catalog",
        "availability_verified": False,
    }
