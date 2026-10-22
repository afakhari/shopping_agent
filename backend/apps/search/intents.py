"""Small, explainable category scopes for ambiguous Persian shopping queries.

This is deliberately not a general semantic classifier. It covers a measured ambiguity
in the supplied dataset (consumer blood-pressure monitors vs industrial/environmental
pressure gauges). Specific model/brand queries are left untouched.
"""
from __future__ import annotations

from dataclasses import dataclass

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
