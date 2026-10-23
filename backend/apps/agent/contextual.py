"""Deterministic, evidence-safe follow-up routing for in-person shopping.

This module never searches a catalogue or invents a product. The server supplies the
last *displayed* product IDs and the canonical prior search query. Ambiguous
references fail closed instead of being converted to a broad OR search.
"""
from __future__ import annotations

import re
from typing import Any

from apps.catalog.services.normalization import normalize_persian_text
from apps.agent.amounts import NUMBER_TOKEN, toman_amount
from apps.agent.dialogue_policy import resolve_dialogue_policy

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
    rf"\s*(?P<amount>{NUMBER_TOKEN})\s*(?P<unit>میلیون|هزار|تومان)?"
)
_CREDIT_NEGATION = re.compile(r"(?:بدون|نمی ?خوام|لازم نیست|نمی ?خوامش).{0,24}(?:قسطی|اعتباری|ترب ?پی)|(?:قسطی|اعتباری).{0,12}(?:نباشه|نمی ?خوام)")
_WHY = re.compile(r"^(?:چرا|به چه دلیل|دلیلش چیه|چرا اینو پیشنهاد دادی|چرا این مدل)(?:.*)?$")
_SELLER_WORDS = re.compile(r"(?:فروشنده|فروشگاه|مغازه|پاساژ)")
_STORE_QUESTION = re.compile(r"(?:ساعت|باز(?:ه| است)|بسته|آدرس|نشانی|کجا|موجودی|تلفن|تماس)")
def _budget_value(message: str) -> str | None:
    match = _BUDGET.search(message)
    if not match:
        return None
    return toman_amount(match.group("amount"), match.group("unit"))


def classify_contextual_turn(message: str, state: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve short follow-ups against the last committed, focused result surface.

    New product requests always remain searches; a price/credit phrase is a
    refinement only if *nothing else* in it names a potentially new product.
    """
    normalized = normalize_persian_text(message).strip(" ؟?!.,؛")
    state = state or {}
    prior = state.get("search_query")
    previous_query = prior.strip() if isinstance(prior, str) else ""
    visible = state.get("visible_product_ids")
    visible_ids = [x for x in visible if isinstance(x, str)] if isinstance(visible, list) else []
    offer_refs = state.get("visible_offer_ids")
    offer_ids = [x for x in offer_refs if isinstance(x, str)] if isinstance(offer_refs, list) else []
    focus = state.get("active_surface", "products")
    if not normalized:
        return {"kind": "clarify", "reply": "چه محصولی را برای خرید حضوری بررسی کنیم؟"}

    policy = resolve_dialogue_policy(normalized, state)
    if policy is not None:
        return dict(policy)

    # "دومی خوبه ولی فروشنده نزدیک تر..." is a structured two-step action.
    combined = re.match(
        r"^(?:مدل |محصول )?(اولی|اول|دومی|دوم|سومی|سوم|چهارمی|چهارم)"
        r"(?: رو| را)? (?:خوبه|می خوام|انتخاب کن|انتخاب کردم|بیشتر دوست دارم)"
        r" (?:ولی|اما|و) (.+)$", normalized
    )
    if combined:
        index = _ORDINALS[combined.group(1)]
        second = combined.group(2)
        if focus != "products" or index >= len(visible_ids):
            return {"kind": "clarify", "reply": "منظورت محصول است یا فروشنده؟ لطفاً از فهرست فعال انتخاب کن."}
        if "فروشنده" in second or "فروشگاه" in second or "نزدیک" in second:
            return {
                "kind": "select_product", "product_id": visible_ids[index], "index": index,
                "explore_sellers": True, "prefer_distance": "نزدیک" in second,
            }
        return {"kind": "clarify", "reply": "مدل موردنظرت مشخص است؛ بخش دوم درخواست را کوتاه‌تر توضیح بده."}

    # Explicit seller noun takes precedence over product focus. Bare ordinals
    # refer ONLY to the currently focused surface, never the history at large.
    ordinal_match = re.search(r"(?<!\S)(اولی|اول|دومی|دوم|سومی|سوم|چهارمی|چهارم)(?!\S)", normalized)
    seller_word = bool(_SELLER_WORDS.search(normalized))
    wants_seller_detail = bool(_STORE_QUESTION.search(normalized))
    if ordinal_match and (
        seller_word or focus == "sellers" or normalized.startswith(("آدرس", "نشانی", "ساعت", "موجودی"))
    ):
        index = _ORDINALS[ordinal_match.group(1)]
        if index < len(offer_ids) and (seller_word or focus == "sellers"):
            kind = "seller_details" if wants_seller_detail else "select_offer"
            return {"kind": kind, "offer_id": offer_ids[index], "index": index}
        return {"kind": "clarify", "reply": "فروشندهٔ موردنظر در فهرست فعال مشخص نیست. یکی از کارت‌های فروشنده را انتخاب کن."}

    # Do not mistake a multi-intent sentence for a standalone ordinal.
    match = _PRODUCT_REF.fullmatch(normalized)
    if match:
        index = _ORDINALS[match.group("ordinal")]
        if focus == "sellers":
            if index < len(offer_ids):
                return {"kind": "select_offer", "offer_id": offer_ids[index], "index": index}
            return {"kind": "clarify", "reply": "فروشندهٔ موردنظر در فهرست فعلی نیست؛ از کارت فروشنده انتخاب کن."}
        if index < len(visible_ids):
            return {"kind": "select_product", "product_id": visible_ids[index], "index": index}
        return {"kind": "clarify", "reply": "این شماره در نتایج فعلی مشخص نیست. نام مدل را بگو یا از کارت همان محصول استفاده کن."}

    # A reported failed physical visit/contact is a recovery request, not
    # a new catalogue product name. It is user-reported, not real verification.
    if re.search(r"(?:جواب نداد|پاسخ نداد|بسته بود|ناموجود بود|موجود نیست|موجود نبود)", normalized):
        if state.get("selected_offer_id"):
            return {"kind": "seller_recovery", "offer_id": state["selected_offer_id"]}
        return {"kind": "clarify", "reply": "کدام فروشگاه پاسخ نداد یا محصول را نداشت؟ از فهرست فروشندگان انتخابش کن تا گزینهٔ جایگزین بیابم."}

    if re.search(r"(?:مقایسه|چه فرقی|فرق(?:ش|شان|شون)?|تفاوت)", normalized):
        compared = state.get("compared_product_ids")
        if isinstance(compared, list) and 2 <= len(compared) <= 3:
            return {"kind": "compare"}
        return {
            "kind": "clarify",
            "reply": "برای مقایسه، دو یا سه محصول از کارت‌ها انتخاب کن؛ سپس تفاوت قیمت و مشخصات ثبت‌شده را نشان می‌دهم.",
        }

    if _WHY.match(normalized):
        return {"kind": "explain"} if previous_query else {
            "kind": "clarify", "reply": "هنوز محصولی پیشنهاد نشده که دلیل انتخابش را بررسی کنم."
        }

    # In-person stock is NEVER verified by a free-form chat message.
    # Ask for explicit consent to run the DEMO simulator for the selected offer.
    # Do not route such a question into an unrelated catalogue search.
    contact_request = (
        ("موجودی" in normalized or "موجوده" in normalized or "موجود هست" in normalized)
        and bool(re.search(r"(?:بررسی|چک|بپرس|استعلام|کن|می خوام|مطمئن|؟|$)", normalized))
    ) or bool(re.search(
        r"(?:استعلام|تماس با فروشنده|از فروشنده بپرس)", normalized
    ))
    if contact_request:
        if state.get("selected_offer_id"):
            return {"kind": "contact_prompt", "offer_id": state["selected_offer_id"]}
        return {
            "kind": "clarify",
            "reply": "برای بررسی آزمایشی موجودی، اول فروشندهٔ همان محصول را انتخاب کن. تماس واقعی انجام نمی‌شود.",
        }

    if normalized in {"فروشنده ها", "فروشنده‌ها", "فروشگاه ها", "فروشگاه‌ها", "فروشنده هاش", "فروشنده هاش رو نشون بده"}:
        if state.get("selected_product_id"):
            return {"kind": "explore_sellers", "product_id": state["selected_product_id"]}
        return {"kind": "clarify", "reply": "کدام مدل؟ ابتدا محصول را از نتیجه‌ها انتخاب کن تا فروشندگان همان مدل را نشان بدهم."}

    # Specific store questions can be answered if the user has explicitly
    # selected an offer. The store coordinates and hours are not live signals.
    if wants_seller_detail and state.get("selected_offer_id") and (
        normalized.startswith(("ساعت", "آدرس", "نشانی", "موجودی", "کجا", "این فروشگاه", "همون فروشگاه"))
        or normalized in {"بازه", "بسته", "آدرسش", "موجودیش"}
    ):
        return {"kind": "seller_details", "offer_id": state["selected_offer_id"]}
    if wants_seller_detail and any(
        x in normalized for x in ("این فروشگاه", "همون فروشگاه", "آدرسش", "ساعتش", "موجودیش")
    ):
        return {"kind": "clarify", "reply": "کدام فروشگاه؟ فروشنده را از فهرست انتخاب کن تا فقط داده‌های ثبت‌شده را توضیح بدهم."}

    value = _budget_value(normalized)
    # A budget-only update has no new product tokens after the amount.
    match_budget = _BUDGET.search(normalized) if value is not None else None
    remainder = (normalized[:match_budget.start()] + " " + normalized[match_budget.end():]).strip() if match_budget else ""
    remainder = re.sub(r"\b(?:م|من|شد|شده|باشه|بشه|بذار|بزار|کن|لطفا|لطفاً|رو|را|دیگه|از|فقط|محدود|نکن)\b", " ", remainder)
    budget_only = bool(match_budget) and not remainder.strip()
    # No token-count shortcuts: "فقط قسطی گوشی میخوام" is a new search,
    # not a credit-only update to a previous laptop mission.
    credit_only = bool(re.fullmatch(
        r"(?:فقط |لطفا |لطفاً |دیگه |دیگر )?(?:قسطی|اعتباری|ترب ?پی)"
        r"(?: باشه| می خوام| میخوام| نمی خوام| نمیخوام| نباشه| لازم نیست)?",
        normalized,
    ))
    sort_only = normalized in {
        "ارزون ترین", "ارزان ترین", "کمترین قیمت",
        "نزدیک ترین", "نزدیکترین", "تازه ترین قیمت",
    }
    if previous_query and (budget_only or credit_only or sort_only):
        updates: dict[str, Any] = {}
        if budget_only:
            updates["max_price_toman"] = value
        if credit_only:
            updates["must_have_in_person_credit"] = not bool(_CREDIT_NEGATION.search(normalized))
        if sort_only:
            updates["sort"] = ("price_asc" if "قیمت" in normalized or "ارزون" in normalized or "ارزان" in normalized
                               else "distance_asc" if "نزدیک" in normalized else "recent_price_change")
        return {"kind": "refine", "query": previous_query, "constraint_updates": updates}

    if not previous_query and (credit_only or budget_only):
        pending: dict[str, Any] = {}
        if budget_only:
            pending["max_price_toman"] = value
        if credit_only:
            pending["must_have_in_person_credit"] = not bool(_CREDIT_NEGATION.search(normalized))
        return {"kind": "clarify", "reply": "شرایط خرید ثبت شد. دنبال چه کالایی در تهران هستی؟",
                "pending_constraints": pending}

    # Ambiguous references must not degrade into noisy catalog search.
    if previous_query and (
        normalized.startswith(("اولی ", "دومی ", "سومی ", "چهارمی ", "مدل اول ", "مدل دوم ", "مدل سوم "))
        or normalized in {"همون", "همین", "این", "اون"}
    ):
        return {"kind": "clarify", "reply": "می‌توانم هر دو مرحله را انجام بدهم؛ فقط مشخص کن منظورت کدام مدل یا فروشگاه است."}
    return {"kind": "search"}
