"""Pure text normalization shared by imports and search queries."""
from __future__ import annotations

import re
import unicodedata

_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)
_WHITESPACE = re.compile(r"\s+")


def normalize_persian_text(value: str | None) -> str:
    """Normalize glyph variants for matching; preserve the original display value elsewhere."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.translate(_DIGITS)
    normalized = normalized.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    normalized = normalized.replace("\u200c", " ").replace("\u200d", " ")
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    return normalized.casefold()
