"""Deterministic, server-controlled store-contact simulator for demo and evaluation."""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Offer, Shop
from apps.missions.models import ContactAttempt, PurchaseMission


_RESPONSE_TEXT = {
    "confirmed_available": "در سناریوی دمو، موجودی محصول تأیید شد.",
    "unavailable": "در سناریوی دمو، کالا موجود نیست؛ گزینه جایگزین بررسی می‌شود.",
    "no_answer": "در سناریوی دمو، فروشگاه پاسخ نداد؛ گزینه جایگزین بررسی می‌شود.",
    "closed": "در سناریوی دمو، فروشگاه بسته است؛ گزینه جایگزین بررسی می‌شود.",
    "error": "استعلام در سناریوی دمو با خطا مواجه شد؛ می‌توان گزینه دیگری را بررسی کرد.",
    "price_changed": "در سناریوی دمو تغییر قیمت گزارش شد؛ قیمت جدید ثبت یا تأیید نشده و نباید از سقف بودجه نتیجه‌گیری کرد.",
}
_ALLOWED_OUTCOMES = set(_RESPONSE_TEXT)


@dataclass(frozen=True)
class SimulationResult:
    attempt: ContactAttempt
    scenario_index: int


def configured_outcomes() -> list[str]:
    raw = getattr(settings, "DEMO_CONTACT_OUTCOMES", "no_answer,confirmed_available,unavailable,closed,error,price_changed")
    outcomes = [item.strip() for item in str(raw).split(",") if item.strip()]
    outcomes = [item for item in outcomes if item in _ALLOWED_OUTCOMES]
    return outcomes or ["no_answer", "confirmed_available", "unavailable", "closed", "error", "price_changed"]


def simulate_contact(
    *,
    mission_id: str,
    shop_id: str,
    offer_id: str,
    purpose: str,
    client_request_id: str | None = None,
) -> SimulationResult:
    """Record a deterministic availability-check result from server config and mission history."""
    if purpose != ContactAttempt.Purpose.VERIFY_AVAILABILITY:
        raise ValidationError({"purpose": "در نسخه فعلی فقط استعلام موجودی شبیه‌سازی می‌شود."})
    with transaction.atomic():
        mission = PurchaseMission.objects.select_for_update().get(pk=mission_id)
        shop = Shop.objects.get(source_id=shop_id)
        offer = Offer.objects.select_related("shop", "product").get(source_id=offer_id)
        if offer.shop_id != shop.source_id:
            raise ValidationError({"offer_id": "این آفر متعلق به فروشگاه انتخاب‌شده نیست."})

        candidate_ids = set((mission.state or {}).get("candidate_product_ids", []))
        if offer.product_id not in candidate_ids:
            raise ValidationError(
                {"offer_id": "ابتدا باید محصول را در همین مأموریت جست‌وجو یا انتخاب کنی."}
            )

        # Respect every current hard condition again at action time (defence in depth).
        constraints = mission.constraints or {}
        if constraints.get("city", "tehran") != "tehran":
            raise ValidationError({"constraints": "این مأموریت خارج از محدوده داده‌های تهران است."})
        if constraints.get("must_have_in_person_credit") and not shop.accepts_in_person_credit:
            raise ValidationError({"shop_id": "فروشگاه شرط خرید اعتباری حضوری مأموریت را ندارد."})
        max_price = constraints.get("max_price_toman")
        if max_price not in (None, "") and (
            offer.price_toman is None or offer.price_toman <= 0 or offer.price_toman > int(max_price)
        ):
            raise ValidationError({"offer_id": "این آفر سقف بودجه مأموریت را رعایت نمی‌کند."})
        lat, lon, radius = constraints.get("lat"), constraints.get("lon"), constraints.get("radius_m")
        if radius is not None and lat is not None and lon is not None:
            # The view also checks the complete hard-filter queryset before reaching this tool.
            from decimal import Decimal
            from apps.search.services import eligible_offer_list

            filters = {
                "must_have_in_person_credit": bool(constraints.get("must_have_in_person_credit")),
                "max_price_toman": Decimal(str(max_price)) if max_price not in (None, "") else None,
                "lat": lat,
                "lon": lon,
                "radius_m": radius,
                "sort": constraints.get("sort", "relevance"),
            }
            if not eligible_offer_list(filters, product_id=offer.product_id).filter(source_id=offer.source_id).exists():
                raise ValidationError({"offer_id": "این آفر خارج از شرایط فعلی مأموریت است."})

        outcomes = configured_outcomes()
        scenario_index = mission.contact_attempts.count() % len(outcomes)
        outcome = outcomes[scenario_index]
        attempt = ContactAttempt.objects.create(
            mission=mission,
            shop=shop,
            offer=offer,
            purpose=purpose,
            outcome=outcome,
            source_type="demo_simulation",
            scenario_index=scenario_index,
            response_text=_RESPONSE_TEXT[outcome],
            client_request_id=client_request_id,
        )
        return SimulationResult(attempt=attempt, scenario_index=scenario_index)


def serialize_contact_attempt(attempt: ContactAttempt) -> dict[str, object]:
    return {
        "id": str(attempt.pk),
        "shop_id": attempt.shop_id,
        "shop_name": attempt.shop.name,
        "offer_id": attempt.offer_id,
        "purpose": attempt.purpose,
        "outcome": attempt.outcome,
        "response_text": attempt.response_text,
        "source_type": attempt.source_type,
        "scenario_index": attempt.scenario_index,
        "created_at": attempt.created_at.isoformat(),
    }
