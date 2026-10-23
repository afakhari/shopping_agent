"""Evidence-aware, persisted visit plans for the offline competition simulator."""
from __future__ import annotations

from urllib.parse import urlencode
from apps.catalog.models import Offer
from apps.catalog.services.visit_context import opening_status, indoor_address_hints
from apps.search.credit import offer_supports_in_person_credit

DAYS = (("sat", "شنبه"), ("sun", "یکشنبه"), ("mon", "دوشنبه"),
        ("tue", "سه‌شنبه"), ("wed", "چهارشنبه"), ("thu", "پنجشنبه"), ("fri", "جمعه"))


def format_weekly_hours(hours: object) -> str:
    if not isinstance(hours, dict) or not hours:
        return "ساعت کاری ثبت نشده"
    rows: list[str] = []
    for key, label in DAYS:
        entry = hours.get(key)
        if not isinstance(entry, dict):
            continue
        if entry.get("status") == "closed":
            rows.append(f"{label}: بسته")
        elif entry.get("status") == "declared":
            shifts = entry.get("shifts")
            if not isinstance(shifts, list):
                continue
            ranges = []
            for shift in shifts:
                if not isinstance(shift, dict):
                    continue
                start, end = shift.get("start_time"), shift.get("end_time")
                if isinstance(start, str) and isinstance(end, str) and len(start) >= 5 and len(end) >= 5:
                    ranges.append(f"{start[:5]} تا {end[:5]}")
            if ranges:
                rows.append(f"{label}: {', '.join(ranges)}")
    return "؛ ".join(rows) if rows else "ساعت کاری ثبت نشده"


def map_url(offer: Offer) -> str | None:
    lat, lon = offer.shop.lat, offer.shop.lon
    if (not isinstance(lat, (int, float)) or isinstance(lat, bool)
        or not isinstance(lon, (int, float)) or isinstance(lon, bool)
        or not -90 <= lat <= 90 or not -180 <= lon <= 180):
        return None
    return "https://www.openstreetmap.org/?" + urlencode({"mlat": str(lat), "mlon": str(lon)}) + f"#map=17/{lat}/{lon}"


def build_visit_plan(offer: Offer, attempt_id: str, backup_offer: dict | None) -> dict:
    shop = backup_offer.get("shop") if isinstance(backup_offer, dict) else None
    backup = None
    if isinstance(shop, dict):
        backup = {
            "shop_id": shop.get("id"),
            "offer_id": backup_offer.get("id"),
            "name": shop.get("name") or "فروشگاه پشتیبان",
            "address": shop.get("address") or shop.get("location_label") or "نشانی ثبت نشده",
            "price_toman": backup_offer.get("price_toman"),
            "status": "آفر ثبت‌شده؛ موجودی فروشگاه پشتیبان استعلام نشده",
        }
    price = f"{offer.price_toman:,.0f} تومان" if offer.price_toman is not None else "قیمت ثبت نشده"
    location_hints = indoor_address_hints(offer.shop.address or offer.shop.location_label)
    hours_status = opening_status(offer.shop.weekly_hours)

    return {
        "title": "خلاصه پیشنهادی مراجعه (فقط سناریوی دمو)",
        "description": "این برنامه تنها برای ارزیابی سناریوی مسابقه است؛ نام بسیاری از فروشگاه‌ها و همه شماره‌های تماس ساختگی هستند. برای مراجعه واقعی از این داده به‌عنوان تأیید هویت یا موجودی استفاده نکن.",
        "status": "موجودی فقط در شبیه‌سازی دمو تأیید شد",
        "source_label": "نتیجه شبیه‌سازی و اطلاعات نمونه: نام اغلب فروشگاه‌ها و همه شماره‌های تماس ساختگی‌اند. تماس واقعی، قیمت فعلی، بازبودن و موجودی تأیید نشده‌اند.",
        "product_id": offer.product_id,
        "shop_id": offer.shop_id,
        "offer_id": offer.source_id,
        "contact_attempt_id": attempt_id,
        "navigation_url": map_url(offer),
        "backup_seller": backup,
        "details": [
            {"key": "product", "label": "محصول", "value": offer.product.persian_title or offer.product_id},
            {"key": "shop", "label": "فروشگاه اصلی", "value": offer.shop.name or offer.shop_id},
            {"key": "price", "label": "قیمت ثبت‌شده", "value": price},
            {"key": "last_price_changed_at", "label": "آخرین تغییر قیمت",
             "value": offer.last_price_changed_at.isoformat() if offer.last_price_changed_at else "زمان تغییر قیمت ثبت نشده"},
            {"key": "address", "label": "نشانی ثبت‌شده",
             "value": offer.shop.address or offer.shop.location_label or "نشانی ثبت نشده"},
            *[
                {"key": key, "label": label, "value": location_hints[key]}
                for key, label in (
                    ("mall", "مرکز خرید یا پاساژ ثبت‌شده"),
                    ("floor", "طبقه ثبت‌شده"),
                    ("unit", "واحد ثبت‌شده"),
                )
                if key in location_hints
            ],
            {"key": "opening_status", "label": "وضعیت بر اساس برنامه ثبت‌شده",
             "value": hours_status["label"]},
            {"key": "weekly_hours", "label": "ساعات ثبت‌شده به وقت تهران",
             "value": format_weekly_hours(offer.shop.weekly_hours)},
            {"key": "in_person_credit", "label": "خرید اعتباری حضوری",
             "value": "آفر واجد شرایط ثبت‌شده" if offer_supports_in_person_credit(offer) else "برای این آفر واجد شرایط ثبت نشده"},
        ],
    }
