"""Conservative shop-visit hints derived only from registered Tehran shop data."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

TEHRAN = ZoneInfo("Asia/Tehran")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_TIME = re.compile(r"^(?:[01]\\d|2[0-3]):[0-5]\\d(?::[0-5]\\d)?$")


def _minute(value: object) -> int | None:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        return None
    hours, minutes = value.split(":")[:2]
    return int(hours) * 60 + int(minutes)


def _valid_shifts(day: object) -> list[tuple[int, int]]:
    if not isinstance(day, dict) or day.get("status") != "declared":
        return []
    shifts = day.get("shifts")
    if not isinstance(shifts, list):
        return []
    valid = []
    for shift in shifts:
        if not isinstance(shift, dict):
            continue
        start = _minute(shift.get("start_time"))
        end = _minute(shift.get("end_time"))
        # 00:00-00:00 is a common placeholder, not a 24-hour promise.
        if start is not None and end is not None and start != end:
            valid.append((start, end))
    return valid


def opening_status(hours: object, at: datetime | None = None) -> dict[str, str]:
    """Evaluate *registered* weekly hours in Tehran, not real-world open status.

    Overnight shifts from yesterday take precedence over today's declared closure.
    Missing, unsupported or malformed schedules remain unknown.
    """
    now = at if at is not None else timezone.now()
    if timezone.is_naive(now):
        raise ValueError("opening_status requires an aware datetime")
    local = now.astimezone(TEHRAN)
    stamp = local.isoformat()
    unknown = {"status": "unknown", "label": "ساعت کاری نامشخص",
               "source": "registered_schedule", "checked_at": stamp}
    if not isinstance(hours, dict):
        return unknown

    current_minute = local.hour * 60 + local.minute
    yesterday = (local - timedelta(days=1)).weekday()
    for start, end in _valid_shifts(hours.get(WEEKDAYS[yesterday])):
        if end < start and current_minute < end:
            return {"status": "open", "label": "طبق برنامه ثبت‌شده باز است",
                    "source": "registered_schedule", "checked_at": stamp}

    entry = hours.get(WEEKDAYS[local.weekday()])
    if not isinstance(entry, dict):
        return unknown
    state = entry.get("status")
    if state == "closed":
        status = "closed"
    elif state == "declared":
        shifts = _valid_shifts(entry)
        if not shifts:
            return unknown
        is_open = any(
            start <= current_minute < end if end > start
            else current_minute >= start
            for start, end in shifts
        )
        status = "open" if is_open else "closed"
    else:
        return unknown
    return {
        "status": status,
        "label": "طبق برنامه ثبت‌شده باز است" if status == "open"
        else "طبق برنامه ثبت‌شده بسته است",
        "source": "registered_schedule",
        "checked_at": stamp,
    }


def indoor_address_hints(address: object) -> dict[str, str]:
    """Extract only verbatim mall, floor and unit fragments; never invent indoor routes."""
    if not isinstance(address, str):
        return {}
    result: dict[str, str] = {}
    mall = re.search(
        r"(پاساژ|مجتمع(?:\\s+تجاری)?|مرکز\\s+خرید)\\s+([^،,؛;\\n]{2,75})",
        address,
    )
    if mall:
        name = re.split(r"\\s+(?=طبقه|واحد|پلاک)\\s*", mall.group(2), maxsplit=1)[0].strip(" .،")
        if name:
            result["mall"] = f"{mall.group(1)} {name}"
    floor = re.search(
        r"طبقه\\s*(?:منفی\\s*)?(?:همکف|زیرزمین|اول|دوم|سوم|چهارم|پنجم|ششم|هفتم|هشتم|نهم|دهم|[0-9۰-۹٠-٩]+)",
        address,
    )
    if floor:
        result["floor"] = floor.group(0).strip()
    unit = re.search(
        r"واحد\\s*(?:شماره\\s*)?[0-9۰-۹٠-٩]+(?:\\s*[-/]\\s*[0-9۰-۹٠-٩]+)?",
        address,
    )
    if unit:
        result["unit"] = unit.group(0).strip()
    return result
