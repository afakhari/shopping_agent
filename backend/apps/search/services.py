"""Database-backed, deterministic catalog search and offer eligibility rules."""
from __future__ import annotations

import math
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import ASin, Cos, Least, Power, Radians, Sin, Sqrt
from django.utils import timezone

from apps.catalog.models import Offer, Product, Shop
from apps.search.credit import eligible_credit_offer_query
from apps.search.intents import CategoryScope, resolve_category_scope

DEFAULT_MAX_REASONABLE_PRICE_TOMAN = 100_000_000_000


def _max_reasonable_price():
    return getattr(settings, "MAX_REASONABLE_PRICE_TOMAN", DEFAULT_MAX_REASONABLE_PRICE_TOMAN)


def _distance_expression(lat: float, lon: float) -> ExpressionWrapper:
    """Haversine distance in metres, expressed with ORM nodes so SQL aliases stay valid."""
    lat_delta = Radians(F("shop__lat") - Value(lat)) / Value(2.0)
    lon_delta = Radians(F("shop__lon") - Value(lon)) / Value(2.0)
    haversine = (
        Power(Sin(lat_delta), Value(2.0))
        + Cos(Radians(Value(lat)))
        * Cos(Radians(F("shop__lat")))
        * Power(Sin(lon_delta), Value(2.0))
    )
    clamped = Least(Value(1.0), haversine)
    distance = Value(2.0 * 6_371_000) * ASin(Sqrt(clamped))
    return ExpressionWrapper(distance, output_field=FloatField())


def _bound_coordinates(lat: float, lon: float, radius_m: int) -> tuple[float, float, float, float]:
    lat_delta = radius_m / 111_320.0
    cos_lat = max(0.01, abs(math.cos(math.radians(lat))))
    lon_delta = radius_m / (111_320.0 * cos_lat)
    return (
        max(-90.0, lat - lat_delta),
        min(90.0, lat + lat_delta),
        max(-180.0, lon - lon_delta),
        min(180.0, lon + lon_delta),
    )


def eligible_offers(filters: dict[str, Any], *, include_distance: bool | None = None):
    """Return only offers that pass every requested hard purchasing constraint.

    An offer with no recorded price is eligible only when no maximum budget is supplied.
    Zero, negative and extreme outlier prices never participate in ranking.
    A catalog offer indicates a listing, not live stock confirmation.
    """
    qs = Offer.objects.select_related("shop", "product")
    max_reasonable = _max_reasonable_price()
    qs = qs.filter(Q(price_toman__isnull=True) | Q(price_toman__range=(1, max_reasonable)))

    budget = filters.get("max_price_toman")
    if budget is not None:
        qs = qs.filter(price_toman__gt=0, price_toman__lte=budget)

    if filters.get("must_have_in_person_credit"):
        # An in-person provider must cover this *offer*, not merely the shop.
        qs = qs.filter(eligible_credit_offer_query())

    lat, lon = filters.get("lat"), filters.get("lon")
    radius_m = filters.get("radius_m")
    wants_distance = include_distance if include_distance is not None else bool(
        lat is not None and lon is not None
    )
    if wants_distance and lat is not None and lon is not None:
        qs = qs.filter(shop__lat__isnull=False, shop__lon__isnull=False)
        if radius_m is not None:
            min_lat, max_lat, min_lon, max_lon = _bound_coordinates(lat, lon, radius_m)
            qs = qs.filter(
                shop__lat__range=(min_lat, max_lat), shop__lon__range=(min_lon, max_lon)
            )
        qs = qs.annotate(distance_m=_distance_expression(lat, lon))
        if radius_m is not None:
            qs = qs.filter(distance_m__lte=radius_m)

    return qs


def offer_ordering(sort: str, has_origin: bool) -> list[Any]:
    if sort == "price_asc":
        return [
            F("price_toman").asc(nulls_last=True),
            F("last_price_changed_at").desc(nulls_last=True),
            "source_id",
        ]
    if sort == "distance_asc" and has_origin:
        return [
            F("distance_m").asc(nulls_last=True),
            F("price_toman").asc(nulls_last=True),
            "source_id",
        ]
    if sort == "recent_price_change":
        return [
            F("last_price_changed_at").desc(nulls_last=True),
            F("price_toman").asc(nulls_last=True),
            "source_id",
        ]
    return [
        F("price_toman").asc(nulls_last=True),
        F("last_price_changed_at").desc(nulls_last=True),
        "source_id",
    ]


def _query_tokens(normalized_query: str) -> list[str]:
    raw = [part for part in normalized_query.split() if len(part) > 1]
    # Keep stable unique tokens and bound query complexity for user-provided natural language.
    return list(dict.fromkeys(raw))[:8] or [normalized_query]


def _product_match_query(normalized_query: str) -> Q:
    query = Q(normalized_title__icontains=normalized_query)
    for token in _query_tokens(normalized_query):
        query |= (
            Q(normalized_title__icontains=token)
            | Q(category_name__icontains=token)
            | Q(brand_name__icontains=token)
            | Q(model__icontains=token)
        )
    return query


def _relevance_expression(normalized_query: str):
    expression = Case(
        When(normalized_title__contains=normalized_query, then=Value(80)),
        default=Value(0),
        output_field=IntegerField(),
    )
    expression += Case(
        When(normalized_title__startswith=normalized_query, then=Value(20)),
        default=Value(0),
        output_field=IntegerField(),
    )
    for token in _query_tokens(normalized_query):
        expression += Case(
            When(normalized_title__icontains=token, then=Value(15)),
            default=Value(0),
            output_field=IntegerField(),
        )
        expression += Case(
            When(category_name__icontains=token, then=Value(7)),
            default=Value(0),
            output_field=IntegerField(),
        )
        expression += Case(
            When(brand_name__icontains=token, then=Value(6)),
            default=Value(0),
            output_field=IntegerField(),
        )
        expression += Case(
            When(model__icontains=token, then=Value(8)),
            default=Value(0),
            output_field=IntegerField(),
        )
    return ExpressionWrapper(expression, output_field=IntegerField())


def product_search_page(filters: dict[str, Any]) -> dict[str, Any]:
    """Search unique products using SQL filters, then paginate after hard constraints."""
    normalized_query = filters["normalized_query"]
    offers = eligible_offers(filters)
    if filters.get("sort") == "distance_asc" and not (filters.get("lat") is not None):
        offers = offers.none()

    category_scope = resolve_category_scope(normalized_query)
    products = Product.objects.filter(_product_match_query(normalized_query))
    if category_scope is not None:
        products = products.filter(category_scope.query)
    products = products.filter(offers__in=offers.order_by().values("source_id")).distinct()
    total = products.count()

    has_origin = filters.get("lat") is not None and filters.get("lon") is not None
    best_offer = offers.filter(product_id=OuterRef("source_id")).order_by(
        *offer_ordering(filters.get("sort", "relevance"), has_origin)
    )
    products = products.annotate(
        relevance_score=_relevance_expression(normalized_query),
        best_offer_source_id=Subquery(best_offer.values("source_id")[:1]),
        best_offer_price_toman=Subquery(best_offer.values("price_toman")[:1]),
        best_offer_changed_at=Subquery(best_offer.values("last_price_changed_at")[:1]),
    )
    if has_origin:
        products = products.annotate(
            best_offer_distance_m=Subquery(best_offer.values("distance_m")[:1])
        )
    else:
        products = products.annotate(best_offer_distance_m=Value(None, output_field=FloatField()))

    sort = filters.get("sort", "relevance")
    if sort == "price_asc":
        products = products.order_by(
            F("best_offer_price_toman").asc(nulls_last=True), "-relevance_score", "source_id"
        )
    elif sort == "distance_asc":
        products = products.order_by(
            F("best_offer_distance_m").asc(nulls_last=True), "-relevance_score", "source_id"
        )
    elif sort == "recent_price_change":
        products = products.order_by(
            F("best_offer_changed_at").desc(nulls_last=True), "-relevance_score", "source_id"
        )
    else:
        products = products.order_by(
            "-relevance_score", F("best_offer_price_toman").asc(nulls_last=True), "source_id"
        )

    page = filters.get("page", 1)
    page_size = filters.get("page_size", 20)
    page_products = list(products[(page - 1) * page_size : page * page_size])
    offer_ids = [
        product.best_offer_source_id for product in page_products if product.best_offer_source_id
    ]
    offer_map = {
        offer.source_id: offer
        for offer in Offer.objects.filter(source_id__in=offer_ids).select_related("shop")
    }
    page_product_ids = [product.source_id for product in page_products]
    counts = {
        row["product_id"]: row["count"]
        for row in offers.filter(product_id__in=page_product_ids)
        .order_by()
        .values("product_id")
        .annotate(count=Count("source_id"))
    }
    results = []
    for product in page_products:
        offer = offer_map.get(product.best_offer_source_id)
        if offer is None:  # Fail closed if an inconsistent row appears during an import.
            continue
        shop_distance = getattr(product, "best_offer_distance_m", None)
        results.append(
            {
                "product": serialize_product(product),
                "best_offer": serialize_offer(offer, shop_distance),
                "eligible_offers_count": counts.get(product.source_id, 0),
                "reasons": _reasons(filters, category_scope),
            }
        )
    return {
        "query": filters.get("q", normalized_query),
        "filters": {
            "max_price_toman": (
                str(filters["max_price_toman"])
                if filters.get("max_price_toman") is not None else None
            ),
            "must_have_in_person_credit": bool(filters.get("must_have_in_person_credit", False)),
            "lat": filters.get("lat"),
            "lon": filters.get("lon"),
            "radius_m": filters.get("radius_m"),
            "sort": sort,
        },
        "page": page,
        "page_size": page_size,
        "total": total,
        "results": results,
        "intent_hint": _intent_hint(category_scope),
    }


def _intent_hint(category_scope: CategoryScope | None) -> dict[str, Any] | None:
    if category_scope is None or not category_scope.defaulted:
        return None
    return {
        "label": category_scope.label,
        "message": category_scope.hint_message,
        "alternative_label": category_scope.alternative_label,
        "alternative_query": category_scope.alternative_query,
    }


def _reasons(filters: dict[str, Any], category_scope: CategoryScope | None = None) -> list[str]:
    reasons = ["تطبیق با عبارت یا واژه‌های جست‌وجو"]
    if filters.get("max_price_toman") is not None:
        reasons.append("آفر انتخاب‌شده داخل سقف بودجه است")
    if filters.get("must_have_in_person_credit"):
        reasons.append("پذیرش خرید اعتباری حضوری برای فروشگاه ثبت شده است")
    if filters.get("radius_m") is not None:
        reasons.append("فروشگاه در شعاع مکانی انتخاب‌شده قرار دارد")
    if category_scope is not None:
        reasons.append(f"با حوزه جست‌وجوی {category_scope.label} مطابقت دارد")
    return reasons


def serialize_product(product: Product) -> dict[str, Any]:
    return {
        "id": product.source_id,
        "title": product.persian_title,
        "brand": product.brand_name,
        "category": product.category_name,
        "model": product.model,
        "images": product.image_urls if isinstance(product.image_urls, list) else [],
        "specs": product.specs if isinstance(product.specs, list) else [],
    }


def serialize_shop(shop: Shop, distance_m: float | None = None) -> dict[str, Any]:
    return {
        "id": shop.source_id,
        "name": shop.name,
        "address": shop.address,
        "location_label": shop.location_label,
        "lat": shop.lat,
        "lon": shop.lon,
        "distance_m": round(float(distance_m)) if distance_m is not None else None,
        "accepts_in_person_credit": shop.accepts_in_person_credit,
    }


def _price_quality(offer: Offer) -> str:
    """Describe amount availability and recency separately from stock confirmation."""
    if offer.price_toman is None:
        return "unknown_price"
    if offer.last_price_changed_at is None:
        return "unknown_timestamp"
    now = timezone.now()
    if offer.last_price_changed_at > now:
        return "unknown_timestamp"
    if offer.last_price_changed_at >= now - timedelta(days=7):
        return "recent_change"
    return "stale"


def serialize_offer(offer: Offer, distance_m: float | None = None) -> dict[str, Any]:
    return {
        "id": offer.source_id,
        "price_toman": str(offer.price_toman) if offer.price_toman is not None else None,
        "last_price_changed_at": (
            offer.last_price_changed_at.isoformat() if offer.last_price_changed_at else None
        ),
        "price_quality": _price_quality(offer),
        "seller_title": offer.seller_title,
        "warranty": offer.warranty if isinstance(offer.warranty, dict) else None,
        "shop": serialize_shop(offer.shop, distance_m),
    }


def serialize_shop_detail(shop: Shop) -> dict[str, Any]:
    return {
        **serialize_shop(shop),
        "category_names": shop.category_names,
        "contacts": shop.contacts,
        "payment_options": shop.payment_options,
        "weekly_hours": shop.weekly_hours,
        "website_url": shop.website_url,
        "instagram": shop.instagram,
        "supports_fast_delivery": shop.supports_fast_delivery,
    }


def eligible_offer_list(filters: dict[str, Any], product_id: str | None = None):
    """Offer collection for a single product, using the same hard eligibility policy."""
    qs = eligible_offers(filters)
    if product_id is not None:
        qs = qs.filter(product_id=product_id)
    return qs.order_by(
        *offer_ordering(
            filters.get("sort", "relevance"), filters.get("lat") is not None
        )
    )
