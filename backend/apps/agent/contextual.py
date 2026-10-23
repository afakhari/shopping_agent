"""Deterministic, evidence-safe follow-up routing for in-person shopping.

This module never searches a catalogue or invents a product. The server supplies the
last *displayed* product IDs and the canonical prior search query. Ambiguous
references fail closed instead of being converted to a broad OR search.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.catalog.services.normalization import normalize_persian_text

_ORDINALS = {"اولی": 0, "اول": 0, "دومی": 1, "دوم": 1,
             "سومی": 2, "سوم": 2, "چهارمی": 3, "چهارم": 3}
_PRODUCT_REF = re.compile(
    r"^(?:(?:این |اون )?(?:مدل|محصول|گزینه) )?"
    r"(?P<ordinal>اولی|اول|دومی|دوم|سومی|سوم|چهارمی|چهارم)"
    r"(?: (?:رو |را )?(?:انتخاب(?: کن| کردم| می کنم)?|می خوام|می پسندم|خوبه|ببین|بیشتر دوست دارم))?$"
)
_BUDGET = re.compile(
    r"(?:بودجه(?: م| من)?|سقف(?: بودجه)?|حداکثر(?: بودجه)?|تا(?: سقف)?)"
    r"(?: (?:م|رو|را|شد|شده|هست|بشه|بکن|کن|رسید|می خوام))*"
    r"\s*(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>میلیون|هزار|تومان)?"
)
_CREDIT = re.compile(r"(?:قسطی|اعتباری|ترب ?پی)")
_CREDIT_NEGATION = re.compile(r"(?:بدون|نمی ?خوام|لازم نیست|نمی ?خوامش).{0,24}(?:قسطی|اعتباری|ترب ?پی)|(?:قسطی|اعتباری).{0,12}(?:نباشه|نمی ?خوام)")
_MORE_GENERAL = re.compile(r"^(?:فقط |لطفا |لطفاً )?(?:قسطی|اعتباری|ترب ?پی)(?: باشه| می خوام)?$")
_WHY = re.compile(r"^(?:چرا|به چه دلیل|دلیلش چیه|چرا اینو پیشنهاد دادی|چرا این مدل)(?:.*)?$")
_SELLER_WORDS = re.compile(r"(?:فروشنده|فروشگاه|مغازه|پاساژ)")
_STORE_QUESTION = re.compile(r"(?:ساعت|باز(?:ه| است)|بسته|آدرس|نشانی|کجا|موجودی|تلفن|تماس)")
_INDEXED = re.compile(r"(?:اولی|دومی|سومی|چهارمی|اول|دوم|سوم|چهارم)")


def _budget_value(message: str) -> str | None:
    match = _BUDGET.search(message)
    if not match:
        return None
    try:
        amount = Decimal(match.group("amount").replace(",", "."))
        unit = match.group("unit")
        if unit == "میلیون":
            amount *= 1_000_000
        elif unit == "هزار":
            amount *= 1_000
        if not amount.is_finite() or amount < 0 or amount >= Decimal("1e30"):
            return None
        return str(amount.quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return None


def classify_contextual_turn(message: str, state: dict[str, Any] | None) -> dict[str, Any]:
    """Return a safe routing decision based on confirmed context, not guessed facts.

    kind: search (normal pipeline), refine (reuse prior catalogue query),
    select_product, explain, clarify. The caller validates every state mutation.
    """
    normalized = normalize_persian_text(message).strip(" ؟?!.,؛")
    state = state or {}
    prior = state.get("search_query")
    previous_query = prior.strip() if isinstance(prior, str) else ""
    visible = state.get("visible_product_ids")
    visible_ids = [x for x in visible if isinstance(x, str)] if isinstance(visible, list) else []
    if not normalized:
        return {"kind": "clarify", "reply": "چه محصولی را برای خرید حضوری بررسی کنیم؟"}

    if _SELLER_WORDS.search(normalized) and _INDEXED.search(normalized):
        return {"kind": "clarify", "reply": "کدام فروشگاه را می گویی؟ ابتدا فروشگاه را از فهرست انتخاب کن؛ شماره فروشگاه را بدون ثبت فهرست حدس نمی زنم."}
    match = _PRODUCT_REF.fullmatch(normalized)
    if match:
        index = _ORDINALS[match.group("ordinal")]
        if index < len(visible_ids):
            return {"kind": "select_product", "product_id": visible_ids[index], "index": index}
        return {"kind": "clarify", "reply": "این شماره در نتایج فعلی مشخص نیست. نام مدل را بگو یا از کارت همان محصول استفاده کن."}

    if _WHY.match(normalized):
        return {"kind": "explain"} if previous_query else {
            "kind": "clarify", "reply": "هنوز محصولی پیشنهاد نشده که دلیل انتخابش را بررسی کنم."
        }

    if _STORE_QUESTION.search(normalized) and (re.search(r"(?:ش|اون|همون|دومی|اولی|این)", normalized) or normalized in {"ساعتش", "آدرسش", "موجودیش"}):
        return {"kind": "clarify", "reply": "نام فروشگاه موردنظرت را مشخص کن تا فقط اطلاعات ثبت شده همان فروشگاه را بررسی کنم."}

    value = _budget_value(normalized)
    credit = bool(_CREDIT.search(normalized))
    credit_only = bool(_MORE_GENERAL.match(normalized))
    sort_only = normalized in {"ارزون ترین", "ارزان ترین", "کمترین قیمت", "نزدیک ترین", "نزدیکترین", "تازه ترین قیمت"}
    budget_only = value is not None and normalized.startswith(
        ("بودجه", "سقف", "حداکثر", "تا ")
    )
    if previous_query and (budget_only or credit_only or sort_only or (
        credit and len(normalized.split()) <= 5 and not _STORE_QUESTION.search(normalized)
    )):
        updates: dict[str, Any] = {}
        if value is not None:
            updates["max_price_toman"] = value
        if credit:
            updates["must_have_in_person_credit"] = not bool(_CREDIT_NEGATION.search(normalized))
        if sort_only:
            updates["sort"] = ("price_asc" if "قیمت" in normalized or "ارزون" in normalized or "ارزان" in normalized
                               else "distance_asc" if "نزدیک" in normalized else "recent_price_change")
        return {"kind": "refine", "query": previous_query, "constraint_updates": updates}

    if not previous_query and (credit_only or budget_only):
        pending: dict[str, Any] = {}
        if value is not None:
            pending["max_price_toman"] = value
        if credit:
            pending["must_have_in_person_credit"] = not bool(_CREDIT_NEGATION.search(normalized))
        return {
            "kind": "clarify",
            "reply": "شرایط خرید ثبت شد. دنبال چه کالایی در تهران هستی؟",
            "pending_constraints": pending,
        }

    # If the ordinal comes with a second task, do not accidentally send it
    # to generic OR text search, and do not silently discard the second task.
    if previous_query and (
        normalized.startswith(("اولی ", "دومی ", "سومی ", "چهارمی ", "مدل اول ", "مدل دوم ", "مدل سوم "))
        or normalized in {"همون", "همین", "این", "اون"}
    ):
        return {
            "kind": "clarify",
            "reply": "منظورت یکی از مدل‌های قبلی است؟ مدل را از کارت انتخاب کن و بعد بگو چه چیزی را درباره آن بررسی کنم.",
        }

    # No product is implied merely because a user mentions "this" or "the second".
    if _INDEXED.search(normalized) and _STORE_QUESTION.search(normalized):
        return {"kind": "clarify", "reply": "منظورت کدام مدل یا فروشگاه است؟ انتخاب را دقیق بگو تا اطلاعات اشتباه نشان ندهم."}
    return {"kind": "search"}
