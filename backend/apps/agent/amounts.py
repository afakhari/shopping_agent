"""Shared budget amount normalization: comma/Arabic separators are not decimals."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

NUMBER_TOKEN = r"(?:\d{1,3}(?:[,٬]\d{3})+|\d+(?:[.,]\d+)?)"


def toman_amount(number: str, unit: str | None = None) -> str | None:
    """Parse grouped integer or fractional amount with explicit Persian scale."""
    raw = number.replace("٬", ",")
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw):
        raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")
    try:
        amount = Decimal(raw)
        if unit == "میلیون":
            amount *= Decimal(1_000_000)
        elif unit == "هزار":
            amount *= Decimal(1_000)
        if not amount.is_finite() or amount < 0 or amount >= Decimal("1e30"):
            return None
        return str(amount.quantize(Decimal("1")))
    except InvalidOperation:
        return None
