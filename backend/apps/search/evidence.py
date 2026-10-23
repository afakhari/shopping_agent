"""Honest, source-backed evidence for an editing-laptop result.

These are observations about the imported snapshot, NOT certification that
specific software or codecs will run well. The user's video resolution and
editing tool are unknown, and live stock/price are not verified.
"""
from __future__ import annotations

import re
from typing import Any

from apps.catalog.services.normalization import normalize_persian_text

# Adobe Premiere (2026) recommends at least 16GB RAM for HD, 32GB+ for 4K.
# These guidelines are advisory: the buyer did not necessarily select Premiere.
_ADOBE_HD_RAM_RECOMMENDED_GB = 16
_ADOBE_4K_RAM_RECOMMENDED_GB = 32
_RAM_KEYS = (
    "مقدار حافظه رم", "ظرفیت حافظه رم", "ظرفیت رم",
    "حجم رم", "حافظه رم", "مقدار رم",
)
_RAM_VALUE = re.compile(r"^(?P<value>\d{1,3})\s*(?:gb|گیگابایت)$")
_RAM_TITLE = re.compile(
    r"(?:\b(?P<before>\d{1,3})\s*gb\s*ram\b|"
    r"\bram\s*(?P<after>\d{1,3})\s*gb\b)",
    flags=re.I,
)
_STORAGE_KEYS = frozenset({
    "نوع حافظه", "نوع حافظه داخلی", "نوع حافظه ذخیره سازی",
    "نوع فضای ذخیره سازی",
})
_USAGE_KEYS = frozenset({"کاربری", "نوع کاربری", "نوع استفاده"})


def editing_laptop_evidence(
    product: Any, *, intensity: str | None = None,
) -> dict[str, Any]:
    """Inspect structured source fields without inferring undocumented specs."""
    raw_specs = product.specs if isinstance(product.specs, list) else []
    known = {}
    for field in raw_specs:
        if not isinstance(field, dict):
            continue
        key, value = field.get("key"), field.get("value")
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        key = normalize_persian_text(key)
        if key not in known and value.strip():
            known[key] = value.strip()

    usage = " ".join(known.get(key, "") for key in _USAGE_KEYS)
    editing_declared = "تدوین" in normalize_persian_text(usage)
    ram_gb = None
    ram_source = None
    for key in _RAM_KEYS:
        match = _RAM_VALUE.fullmatch(normalize_persian_text(known.get(key, "")))
        if match:
            ram_gb = int(match.group("value"))
            ram_source = "spec"
            break
    if ram_gb is None:
        title = normalize_persian_text(getattr(product, "persian_title", "") or "")
        title_match = _RAM_TITLE.search(title)
        if title_match:
            ram_gb = int(title_match.group("before") or title_match.group("after"))
            ram_source = "title"

    ssd_stated = any(
        "ssd" in normalize_persian_text(known.get(key, ""))
        for key in _STORAGE_KEYS
    )
    # The title is a weaker source, but can still state a concrete SSD explicitly.
    if not ssd_stated:
        ssd_stated = bool(re.search(
            r"\bssd\b", normalize_persian_text(
                getattr(product, "persian_title", "") or ""
            )
        ))
    preferred_ram = (
        _ADOBE_4K_RAM_RECOMMENDED_GB if intensity == "heavy"
        else _ADOBE_HD_RAM_RECOMMENDED_GB
    )
    adobe_example = "4K" if intensity == "heavy" else "HD"
    notes: list[str] = []
    if editing_declared:
        notes.append("کاربری تدوین در مشخصات ثبت شده است")
    if ram_gb is None:
        notes.append("ظرفیت RAM از دادهٔ معتبر همین مدل مشخص نیست")
    elif ram_gb < preferred_ram:
        notes.append(
            f"RAM ثبت‌شده {ram_gb} گیگابایت است؛ کمتر از مقدار پیشنهادی "
            "Adobe Premiere برای ویدیوی {adobe_example}"
        )
    else:
        notes.append(
            f"RAM ثبت‌شده {ram_gb} گیگابایت است؛ از مقدار پیشنهادی "
            "Adobe Premiere برای ویدیوی {adobe_example} کمتر نیست"
        )
    if ssd_stated:
        notes.append("ذخیره‌سازی SSD در دادهٔ این مدل ذکر شده است")
    return {
        "source": "snapshot_catalog",
        "use_case": "video_editing",
        "intensity": intensity if intensity in {"light", "heavy"} else None,
        "usage_declared": editing_declared,
        "ram_gb": ram_gb,
        "ram_source": ram_source,
        "ssd_stated": ssd_stated,
        "notes": notes,
        "suitability_verified": False,
        "caveat": (
            "این داده‌ها برای تایید مناسب‌بودن قطعی تدوین کافی نیستند. "
            "نرم‌افزار، وضوح و کدک ویدئو، پردازنده و گرافیک هر مدل باید جداگانه بررسی شوند."
        ),
    }
