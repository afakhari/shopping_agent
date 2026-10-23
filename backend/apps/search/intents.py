"""Small, explainable category scopes for ambiguous Persian shopping queries.

This is deliberately not a general semantic classifier. It covers a measured ambiguity
in the supplied dataset (consumer blood-pressure monitors vs industrial/environmental
pressure gauges). Specific model/brand queries are left untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from django.db.models import Q


@dataclass(frozen=True)
class CategoryScope:
    key: str
    label: str
    query: Q
    defaulted: bool = False
    hint_message: str | None = None
    alternative_label: str | None = None
    alternative_query: str | None = None


# Catalog taxonomy, not lexical title overlap, decides whether a query for a
# laptop refers to a computer, an accessory, or a children's educational toy.
# The supplied snapshot uses "لپ تاپ و نوت بوک" for actual computers; using an
# unrestricted OR title search was returning chargers, bags and toy laptops.
_LAPTOP_QUERY = re.compile(r"(?<!\w)(?:لپ\s*تاپ|لپتاپ|نوت\s*بوک)(?!\w)")
_LAPTOP_ACCESSORY_SCOPES = (
    (("آموزشی کودک", "اسباب بازی", "اسباب‌بازی"), "toy_laptop", "لپ‌تاپ آموزشی کودک",
     ("لپ تاپ اسباب بازی", "اسباب بازی")),
    (("شارژر", "آداپتور"), "laptop_charger", "شارژر لپ‌تاپ",
     ("شارژر لپ تاپ", "آداپتور برق")),
    (("کیف", "کاور", "کوله"), "laptop_bag", "کیف و کاور لپ‌تاپ",
     ("کیف و کاور لپ تاپ", "کیف و کوله")),
    (("باتری",), "laptop_battery", "باتری لپ‌تاپ", ("باتری لپ تاپ",)),
    (("رم", "ram"), "laptop_ram", "رم لپ‌تاپ", ("رم لپ تاپ",)),
    (("استند", "پایه", "خنک کننده", "کول پد"), "laptop_stand", "پایه لپ‌تاپ",
     ("پایه نگهدارنده مانیتور و لپ تاپ", "استند و پایه خنک کننده")),
    (("برچسب", "استیکر"), "laptop_sticker", "برچسب لپ‌تاپ",
     ("برچسب و استیکر موبایل و لپ تاپ",)),
    (("فن",), "laptop_fan", "فن لپ‌تاپ", ("فن لپ تاپ",)),
)


def _resolve_laptop_scope(query: str) -> CategoryScope | None:
    if _LAPTOP_QUERY.search(query) is None:
        return None
    tokens = query.split()
    for cues, key, label, categories in _LAPTOP_ACCESSORY_SCOPES:
        # "لپ تاپ با رم زیاد" is a COMPUTER request, not a RAM stick.
        # Accessory intent must begin with that accessory noun. Exception:
        # educational toy laptops, whose noun starts with laptop.
        accessory_first = bool(tokens) and any(
            query.startswith(cue + " ") or query == cue for cue in cues
        )
        toy_explicit = key == "toy_laptop" and (
            "آموزشی کودک" in query or "اسباب بازی" in query
        )
        if accessory_first or toy_explicit:
            category_query = Q()
            for category in categories:
                category_query |= Q(category_name__icontains=category)
            return CategoryScope(key=key, label=label, query=category_query)
    # A laptop request must never become a bag/charger search solely because
    # an accessory's title contains the words "لپ تاپ".
    return CategoryScope(
        key="laptop_computer",
        label="لپ‌تاپ و نوت‌بوک",
        query=(
            Q(category_name__icontains="لپ تاپ و نوت بوک")
            | Q(category_name__iexact="لپ تاپ")
            | Q(category_name__iexact="لپتاپ")
            | Q(category_name__iexact="نوت بوک")
        ),
    )


# Extend category-first retrieval to the most frequent consumer families.
# A category is a ground-truth catalogue facet; a matching token in a charger
# or phone cover is not evidence that the item is a phone.
_PRODUCT_FAMILIES = (
    ("گوشی", "گوشی موبایل", ("گوشی موبایل",)),
    ("هدفون", "هدفون و هندزفری", ("هدفون، هدست و هندزفری", "هدفون")),
    ("تلویزیون", "تلویزیون", ("تلویزیون",)),
    ("تبلت", "تبلت", ("تبلت",)),
)
_ACCESSORY_HEADS = frozenset({
    "کیف", "کاور", "شارژر", "باتری", "محافظ", "پایه", "گلس", "برچسب",
})


def _resolve_consumer_scope(query: str) -> CategoryScope | None:
    for word, label, categories in _PRODUCT_FAMILIES:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", query) is None:
            continue
        # Distinguish an explicit accessory request by its initial noun.
        head = query.split(maxsplit=1)[0]
        if head in _ACCESSORY_HEADS:
            return CategoryScope(
                key=f"{word}_accessory",
                label=f"{head} {word}",
                query=Q(category_name__icontains=head) & Q(category_name__icontains=word),
            )
        if word == "گوشی" and "پزشکی" in query:
            return CategoryScope(
                key="medical_stethoscope", label="گوشی پزشکی",
                query=Q(category_name__iexact="گوشی پزشکی"),
            )
        category_query = Q()
        for category in categories:
            category_query |= Q(category_name__iexact=category)
        return CategoryScope(
            key=f"{word}_product", label=label, query=category_query,
        )
    return None


_PRESSURE_TRIGGERS = ("فشارسنج", "فشار سنج", "بارومتر", "مانومتر")
_INDUSTRIAL_CUES = (
    "صنعتی", "محیطی", "بارومتر", "مانومتر", "گیج فشار", "درجه باد",
    "ترانسمیتر", "فشار باد", "لاستیک", "هواشناسی",
)
_MEDICAL_CUES = (
    "پزشکی", "فشار خون", "خون", "بازویی", "خانگی", "دیجیتال", "دیجیتالی",
    "بیورر", "امرون", "امرن", "آرم استایل",
)
_GENERIC_TOKENS = {
    "فشارسنج", "فشار", "سنج", "قیمت", "خرید", "ارزان", "ارزانترین", "بهترین",
    "مدل", "امروز", "تهران", "حضوری", "دیجیتال", "دیجیتالی", "خانگی", "پزشکی",
    "بازویی", "خون", "برای", "من", "یه", "یک", "لطفا", "لطفاً", "میخوام",
    "میخواهم", "می خوام", "می خواهم", "بخرم", "ترین", "کمترین", "بیشترین",
    "ارزون", "ارزونترین",
}


def resolve_category_scope(normalized_query: str) -> CategoryScope | None:
    """Resolve the pressure-gauge ambiguity only when the query carries enough signal.

    A bare/common consumer query defaults to medical monitors and provides an explicit
    alternative. Clear industrial terms select industrial categories. Unknown extra tokens
    (e.g. a specific brand/model) disable automatic scoping so exact searches stay broad.
    """
    query = " ".join((normalized_query or "").split())
    laptop_scope = _resolve_laptop_scope(query)
    if laptop_scope is not None:
        return laptop_scope
    consumer_scope = _resolve_consumer_scope(query)
    if consumer_scope is not None:
        return consumer_scope
    if not any(trigger in query for trigger in _PRESSURE_TRIGGERS):
        return None

    if any(cue in query for cue in _INDUSTRIAL_CUES):
        industrial_categories = (
            "بارومتر", "گیج فشار", "مانومتر", "درجه باد", "ترانسمیتر فشار",
            "دماسنج و رطوبت سنج", "ماژول های الکترونیکی", "دیتالاگر",
        )
        category_query = Q()
        for category in industrial_categories:
            category_query |= Q(category_name__icontains=category)
        return CategoryScope(
            key="pressure_industrial",
            label="فشارسنج محیطی و صنعتی",
            query=category_query,
        )

    if any(cue in query for cue in _MEDICAL_CUES):
        return CategoryScope(
            key="pressure_medical",
            label="فشارسنج پزشکی",
            query=Q(category_name__icontains="فشارسنج پزشکی"),
        )

    tokens = set(query.split())
    if tokens and tokens <= _GENERIC_TOKENS:
        return CategoryScope(
            key="pressure_medical",
            label="فشارسنج پزشکی",
            query=Q(category_name__icontains="فشارسنج پزشکی"),
            defaulted=True,
            hint_message=(
                "برای عبارت عمومی «فشارسنج»، ابتدا مدل‌های پزشکی را نشان می‌دهیم تا با "
                "بارومترها و تجهیزات صنعتی مخلوط نشوند."
            ),
            alternative_label="دیدن فشارسنج‌های صنعتی و محیطی",
            alternative_query="فشارسنج صنعتی",
        )

    # A specific brand/model or an unfamiliar modifier should not be silently reinterpreted.
    return None
