"""Explicit, grounded recommendation slot filling for frequent shopping families.

All returned search plans use a whitelisted category query. No conversation
history or generated prose is ever treated as a new product name. This module
does not search, call models, or claim stock availability.
"""
from __future__ import annotations

import re
from typing import Any, TypedDict

from apps.agent.amounts import NUMBER_TOKEN, toman_amount
from apps.catalog.services.normalization import normalize_persian_text


class RecommendationDecision(TypedDict, total=False):
    kind: str
    reply: str
    pending_dialogue: dict[str, str] | None
    query_override: str
    constraint_updates: dict[str, Any]
    usage_profile: str
    shopping_need: dict[str, str]


_CANONICAL = {
    "laptop": "لپ تاپ",
    "phone": "گوشی",
    "headphones": "هدفون",
    "tablet": "تبلت",
    "television": "تلویزیون",
}
_FAMILIES = (
    ("laptop", re.compile(r"(?:لپ\s*تاپ\w*|لپتاپ\w*|نوت\s*بوک\w*)")),
    ("phone", re.compile(r"(?<!\w)(?:گوشی|موبایل)(?!\w)")),
    ("headphones", re.compile(r"(?<!\w)(?:هدفون|هندزفری)(?:ی)?(?!\w)")),
    ("tablet", re.compile(r"(?<!\w)تبلت(?:ی)?(?!\w)")),
    ("television", re.compile(r"(?<!\w)تلویزیون(?!\w)")),
)
_ACCESSORY_FIRST = re.compile(
    r"^(?:برای\s+)?(?:کیف|کاور|کوله|شارژر|آداپتور|محافظ|گلس|پایه|"
    r"استند|باتری|رم|فن|برچسب|استیکر)(?:\s+|$)"
)
_RECOMMENDATION = re.compile(
    r"(?:چه\s+(?:لپ|گوشی|هدفون|هندزفری|تبلت|تلویزیون|موبایل)"
    r"|کدوم\s+|کدام\s+|بهترین\s+|چه\s+مدلی\s+|چه\s+گزینه)"
)
_USE_CASES = (
    ("video_editing", re.compile(r"(?:تدوین|ادیت\s*(?:فیلم|ویدیو)|ویرایش\s*(?:فیلم|ویدیو)|پریمیر|افترافکت)")),
    ("gaming", re.compile(r"(?:گیمینگ|بازی\s*(?:کامپیوتری|سنگین)|گیم)")),
    ("photography", re.compile(r"(?:عکاسی|عکس\s*برداری)")),
    ("presentation", re.compile(r"(?:پخش\s*(?:عکس|موسیقی|آهنگ)|اسلاید|پروژکتور)")),
    ("study", re.compile(r"(?:دانشجویی|دانشگاه|درس|آموزشی)")),
)
_BUDGET = re.compile(
    rf"(?:بودجه|قیمت|سقف(?:\s*بودجه)?|حداکثر|حدود|تا(?:\s*سقف)?|زیر|"
    rf"کمتر\s+از)\s*(?:من\s*|م\s*|تا\s*|حدود\s*)?"
    rf"(?P<number>{NUMBER_TOKEN})\s*(?P<unit>میلیون|هزار|تومان)?"
)
_SHORT_BUDGET = re.compile(
    rf"^(?:تا\s*|حدود\s*|فقط\s*)?(?P<number>{NUMBER_TOKEN})\s*"
    r"(?P<unit>میلیون|هزار|تومان)\s*(?:تومان)?$"
)
_CANCEL = re.compile(r"^(?:بی\s*خیال|ولش\s*کن|لغو|کنسل|نمی\s*خوام|منصرف\s*شدم)$")
_NEW_PRODUCT = re.compile(r"(?:می\s*خوام|می\s*خواهم|بخرم|بخر|معرفی\s*کن|پیدا\s*کن)")
_ADVICE_INTERRUPT = re.compile(
    r"(?:\?|؟|آیا|چرا|چطور|لازم|نیاز|باید|چه\s*فرقی|تفاوت|گرافیک|"
    r"پردازنده|رم|حافظه|چه\s*ویژگی)"
)


def _family(message: str) -> str | None:
    if _ACCESSORY_FIRST.match(message) or "گوشی پزشکی" in message:
        return None
    matches = [key for key, pattern in _FAMILIES if pattern.search(message)]
    return matches[0] if len(matches) == 1 else None


def _usage(message: str) -> str | None:
    for name, pattern in _USE_CASES:
        if pattern.search(message):
            return name
    return None


def _budget(message: str, *, pending: bool = False) -> str | None:
    match = _BUDGET.search(message)
    if match is None and pending:
        match = _SHORT_BUDGET.fullmatch(message)
    if not match:
        return None
    return toman_amount(match.group("number"), match.group("unit"))


def _continue(family: str, usage: str | None, budget: str | None, intensity: str) -> RecommendationDecision:
    need = {"family": family, "usage": usage or "", "intensity": intensity}
    if not usage:
        return {
            "kind": "clarify",
            "reply": f"برای انتخاب {_CANONICAL[family]}، کاربرد اصلی‌ات چیست؟ "
                     "اگر بودجه‌ای در نظر داری همان را هم بگو.",
            "pending_dialogue": {
                "slot": "recommendation_usage", **need,
                **({"budget": budget} if budget else {}),
            },
        }
    if not budget:
        return {
            "kind": "clarify",
            "reply": f"برای {_CANONICAL[family]} با این کاربرد، سقف بودجه‌ات چند تومان است؟ "
                     "بعد فقط کالاهای همان دسته را با آفرهای داخل بودجه بررسی می‌کنم.",
            "pending_dialogue": {"slot": "recommendation_budget", **need},
        }
    return {
        "kind": "search",
        "query_override": _CANONICAL[family],
        "constraint_updates": {"max_price_toman": budget},
        "usage_profile": usage,
        "shopping_need": need,
        "pending_dialogue": None,
    }


def resolve_recommendation_frame(
    message: str, state: dict[str, Any] | None,
) -> RecommendationDecision | None:
    normalized = normalize_persian_text(message).strip(" ؟?!.,؛")
    state = state or {}
    old = state.get("pending_dialogue")
    pending = old if isinstance(old, dict) and (
        old.get("slot") == "recommendation_family"
        or (
            old.get("slot") in ("recommendation_usage", "recommendation_budget")
            and old.get("family") in _CANONICAL
        )
    ) else None
    explicit_family = _family(normalized)

    if pending:
        if _CANCEL.fullmatch(normalized):
            return {
                "kind": "clarify",
                "reply": "درخواست قبلی کنار گذاشته شد. حالا دنبال چه محصولی هستی؟",
                "pending_dialogue": None,
            }
        if pending["slot"] == "recommendation_family":
            if explicit_family:
                return _continue(
                    explicit_family, _usage(normalized) or pending.get("usage") or None,
                    _budget(normalized, pending=True) or pending.get("budget"),
                    "light" if "سبک" in normalized else pending.get("intensity") or "",
                )
            return {
                "kind": "clarify",
                "reply": "برای این کاربرد دنبال چه نوع کالایی هستی؟ "
                         "مثلاً لپ‌تاپ، تبلت یا محصول دیگری؟",
                "pending_dialogue": dict(pending),
            }
        if explicit_family and explicit_family != pending["family"]:
            # The ordinary search router is responsible for the new category.
            return None
        if explicit_family is None and _ACCESSORY_FIRST.match(normalized):
            return None
        budget = _budget(normalized, pending=True) or pending.get("budget")
        usage = _usage(normalized) or pending.get("usage") or None
        intensity = (
            "heavy" if re.search(r"(?:سنگین|4k|4کی|فورکی)", normalized)
            else "light" if re.search(r"(?:سبک|ساده|full\s*hd|1080p)", normalized)
            else pending.get("intensity") or ""
        )
        # Unrelated questions are handled by the original advice router without
        # closing or mutating this pending frame. Pure budget/usage replies fill it.
        has_fill = _usage(normalized) or _budget(normalized, pending=True)
        if not has_fill:
            if _ADVICE_INTERRUPT.search(message):
                return None
            if explicit_family and _NEW_PRODUCT.search(normalized):
                # User requests the same category again; the original intent
                # can be routed normally rather than silently searching.
                return None
            return {
                "kind": "clarify",
                "reply": "هنوز برای ادامه پیشنهاد خرید به کاربرد و بودجه نیاز دارم. "
                         "کاربرد یا سقف بودجه را مشخص کن.",
                "pending_dialogue": dict(pending),
            }
        return _continue(pending["family"], usage, budget, intensity)

    if not explicit_family:
        # Use-case + budget alone must never become a category-free OR search.
        # Ask for the missing family, carrying the known constraints as slots.
        unknown_use = _usage(normalized)
        known_budget = _budget(normalized)
        if unknown_use and known_budget:
            return {
                "kind": "clarify",
                "reply": "کاربرد و بودجه را متوجه شدم. می‌خواهی چه کالایی بخری؟ "
                         "لپ‌تاپ، رایانه رومیزی یا محصول دیگری؟",
                "pending_dialogue": {
                    "slot": "recommendation_family", "usage": unknown_use,
                    "budget": known_budget,
                    "intensity": "light" if "سبک" in normalized else "",
                },
            }
        return None
    # Only guided recommendation questions create a persistent form; a direct
    # explicit product/model request still follows the standard catalog path.
    recommending = bool(
        _RECOMMENDATION.search(normalized)
        or ("مناسب" in normalized and (
            "؟" in message or "?" in message
            or _usage(normalized) or _budget(normalized)
        ))
    )
    if not recommending or _ACCESSORY_FIRST.match(normalized):
        return None
    # Explicit brand/model and GPU-SKU requests need exact lexical matching,
    # not replacement by the broad canonical product family.
    if re.search(r"(?<!\w)(?:rtx|gtx|rx)\s*\d{3,4}(?!\w)", normalized):
        return None
    if re.search(r"(?<!\w)مدل\s+[a-z0-9]", normalized):
        return None
    # Do not accidentally turn technical support / purchase-spec questions
    # into a catalog recommendation flow.
    if re.search(r"(?:گرافیک|پردازنده|رم|باتری)\s*(?:لازم|نیاز|باید)", normalized):
        return None
    return _continue(
        explicit_family,
        _usage(normalized),
        _budget(normalized),
        "heavy" if re.search(r"(?:سنگین|4k|4کی|فورکی)", normalized)
        else "light" if re.search(r"(?:سبک|ساده|full\s*hd|1080p)", normalized)
        else "",
    )
