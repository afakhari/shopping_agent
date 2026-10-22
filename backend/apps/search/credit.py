"""Conservative offer-level eligibility for registered in-person credit options.

A shop advertising a credit provider is insufficient evidence that every product and
amount is accepted. Build a DB predicate from the published shop-specific constraints,
so pagination, counts, ordering and contact-time validation share the same rules.
Unknown channels, malformed limits and unsupported categories fail closed.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db.models import Q

from apps.catalog.models import Shop


def _positive_bound(value: object) -> Decimal | None:
    """A null/zero bound means no bound; malformed values invalidate an option."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean price limit")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid credit price limit") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid credit price limit")
    return amount if amount > 0 else None


def eligible_credit_offer_query() -> Q:
    """Return a Q selecting offers eligible for at least one in-person provider.

    Read current database state rather than a cached shop flag; a provider's
    min/max price and category limitations belong to individual offers.
    A shop category is not proof of product availability: callers join Offer.
    """
    allowed = Q(pk__in=[])
    for shop in Shop.objects.filter(accepts_in_person_credit=True).only("source_id", "payment_options"):
        if not isinstance(shop.payment_options, list):
            continue
        for option in shop.payment_options:
            if not isinstance(option, dict) or option.get("channel") != "in_person":
                continue
            try:
                min_price = _positive_bound(option.get("min_price_toman"))
                max_price = _positive_bound(option.get("max_price_toman"))
            except ValueError:
                continue
            if min_price is not None and max_price is not None and min_price > max_price:
                continue
            categories = option.get("category_names", [])
            if not isinstance(categories, list):
                continue
            if any(not isinstance(name, str) for name in categories):
                continue
            clause = Q(shop_id=shop.source_id)
            if min_price is not None:
                clause &= Q(price_toman__gte=min_price)
            if max_price is not None:
                clause &= Q(price_toman__lte=max_price)
            if categories:
                exact_categories = [name.strip() for name in categories if name.strip()]
                if not exact_categories:
                    continue
                clause &= Q(product__category_name__in=exact_categories)
            allowed |= clause
    return allowed


def offer_supports_in_person_credit(offer) -> bool:
    """Display only credit verified by the same offer-level conditions used in search."""
    shop = offer.shop
    if not shop.accepts_in_person_credit or not isinstance(shop.payment_options, list):
        return False
    for option in shop.payment_options:
        if not isinstance(option, dict) or option.get("channel") != "in_person":
            continue
        try:
            min_price = _positive_bound(option.get("min_price_toman"))
            max_price = _positive_bound(option.get("max_price_toman"))
        except ValueError:
            continue
        if min_price is not None and max_price is not None and min_price > max_price:
            continue
        categories = option.get("category_names", [])
        if not isinstance(categories, list) or any(
            not isinstance(name, str) for name in categories
        ):
            continue
        if categories and offer.product.category_name not in [
            name.strip() for name in categories if name.strip()
        ]:
            continue
        if min_price is not None and (
            offer.price_toman is None or offer.price_toman < min_price
        ):
            continue
        if max_price is not None and (
            offer.price_toman is None or offer.price_toman > max_price
        ):
            continue
        return True
    return False
