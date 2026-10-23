"""Fail-closed, intentionally user-triggered Neshan distance-matrix adapter.

Only the fixed, allowlisted HTTPS endpoint can be called. No customer-supplied
URL, credential, destination coordinates or persistent route cache.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from django.conf import settings

_MATRIX_URL = "https://api.neshan.org/v1/distance-matrix"
_MAX_BODY = 48_000


class RoutingUnavailable(Exception):
    """A provider error must never be presented as a real ETA."""

    def __init__(self, reason: str = "provider_unavailable"):
        self.reason = reason
        super().__init__(reason)


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def neshan_enabled() -> bool:
    return bool(
        getattr(settings, "NESHAN_ROUTING_ENABLED", False)
        and getattr(settings, "NESHAN_ROUTING_API_KEY", "")
        and getattr(settings, "NESHAN_ROUTING_MAX_CALLS_PER_MISSION", 0) > 0
        and getattr(settings, "NESHAN_ROUTING_DAILY_MAX_CALLS", 0) > 0
    )


def _point(lat: float, lon: float) -> str:
    if not all(math.isfinite(v) for v in (lat, lon)):
        raise RoutingUnavailable("invalid_coordinates")
    return f"{lat:.6f},{lon:.6f}"


def read_matrix(
    origin: tuple[float, float],
    destinations: list[tuple[float, float]],
    mode: str,
) -> list[dict]:
    """Return one normalized element per destination; no fake fallback values."""
    if not neshan_enabled():
        raise RoutingUnavailable("not_configured")
    if mode not in {"car", "motorcycle"} or not 1 <= len(destinations) <= 5:
        raise RoutingUnavailable("invalid_request")
    params = urlencode({
        "type": mode,
        "origins": _point(*origin),
        "destinations": "|".join(_point(*destination) for destination in destinations),
    })
    request = Request(
        f"{_MATRIX_URL}?{params}",
        headers={"Api-Key": settings.NESHAN_ROUTING_API_KEY, "Accept": "application/json"},
        method="GET",
    )
    opener = build_opener(HTTPSHandler(), _NoRedirects())
    try:
        with opener.open(request, timeout=3.5) as response:
            if response.status != 200:
                raise RoutingUnavailable("provider_unavailable")
            raw = response.read(_MAX_BODY + 1)
        if len(raw) > _MAX_BODY:
            raise RoutingUnavailable("invalid_response")
        payload = json.loads(raw)
    except HTTPError as exc:
        if exc.code in {480, 481, 482, 483, 484, 485}:
            raise RoutingUnavailable("quota_or_key_unavailable") from None
        raise RoutingUnavailable("provider_unavailable") from None
    except (OSError, ValueError):
        raise RoutingUnavailable("provider_unavailable") from None
    if not isinstance(payload, dict) or payload.get("status") != "Ok":
        raise RoutingUnavailable("invalid_response")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 1:
        raise RoutingUnavailable("invalid_response")
    elements = rows[0].get("elements") if isinstance(rows[0], dict) else None
    if not isinstance(elements, list) or len(elements) != len(destinations):
        raise RoutingUnavailable("invalid_response")
    parsed = []
    for element in elements:
        if not isinstance(element, dict):
            parsed.append({"status": "unknown_error"})
            continue
        if element.get("status") == "NoRoute":
            parsed.append({"status": "no_route"})
            continue
        if element.get("status") != "Ok":
            parsed.append({"status": "unknown_error"})
            continue
        duration = element.get("duration")
        distance = element.get("distance")
        seconds = duration.get("value") if isinstance(duration, dict) else None
        meters = distance.get("value") if isinstance(distance, dict) else None
        if (
            isinstance(seconds, (int, float)) and not isinstance(seconds, bool)
            and isinstance(meters, (int, float)) and not isinstance(meters, bool)
            and math.isfinite(seconds) and math.isfinite(meters)
            and 0 < seconds < 86_400 and 0 <= meters < 1_000_000
        ):
            parsed.append({
                "status": "ok",
                "duration_seconds": int(round(seconds)),
                "route_distance_meters": int(round(meters)),
            })
        else:
            parsed.append({"status": "unknown_error"})
    return parsed


def safe_response(*, mode: str, status: str = "unavailable",
                  reason: str = "not_configured") -> dict:
    return {
        "provider": "neshan", "mode": mode, "status": status,
        "reason": reason, "estimates": [],
        "availability_verified": False, "source": "provider_route_estimate",
    }


def successful_response(*, mode: str, offers: list, matrix: list[dict]) -> dict:
    return {
        "provider": "neshan", "mode": mode, "status": "ok",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "estimates": [{"offer_id": offer.source_id, **result}
                      for offer, result in zip(offers, matrix, strict=True)],
        "availability_verified": False, "source": "provider_route_estimate",
    }
