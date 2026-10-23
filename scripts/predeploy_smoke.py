#!/usr/bin/env python3
"""Read-only public release smoke, with optional no-LLM session ownership checks."""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

DEFAULT_QUERY = "هدفون"


def validate_base_url(value: str, allow_http_local: bool = False) -> str:
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("Only the public origin is accepted; no paths, credentials or query strings.")
    if parsed.scheme == "https" and parsed.hostname:
        return value.rstrip("/")
    if (allow_http_local and parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1"}):
        return value.rstrip("/")
    raise ValueError("Use HTTPS, or --allow-http-local with 127.0.0.1/localhost.")


def fetch(opener, base: str, path: str, *, payload: dict | None = None,
          timeout: float = 10) -> tuple[int, dict, object]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base + path, data=data, headers=headers,
                      method="POST" if data is not None else "GET")
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        status = response.status
        meta = response.headers
        content = response.read(1_000_000)
    try:
        parsed = json.loads(content.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON object expected")
    except (UnicodeError, ValueError) as exc:
        raise AssertionError(f"{path}: invalid JSON HTTP {status}") from exc
    return status, parsed, meta


def perform(base: str, *, active: bool = False,
            require_configured: bool = False, timeout: float = 10) -> list[str]:
    checks: list[str] = []
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    status, live, _ = fetch(opener, base, "/api/v1/health/live/", timeout=timeout)
    assert status == 200 and live.get("status") == "alive", "Liveness probe failed"
    checks.append("live=ok")
    status, ready, _ = fetch(opener, base, "/api/v1/health/ready/", timeout=timeout)
    assert status == 200 and ready.get("status") == "ready", "Readiness probe failed"
    assert ready.get("checks", {}).get("database") == "ok", "Database is not ready"
    assert ready.get("checks", {}).get("catalog") == "ok", "Full dataset is not ready"
    if require_configured:
        assert ready.get("agent_mode") == "model_configured", "Model is not configured"
    checks.append("database-and-catalog=ok")

    search_path = "/api/v1/catalog/search/?" + urlencode({"q": DEFAULT_QUERY, "page_size": 3})
    status, results, _ = fetch(opener, base, search_path, timeout=timeout)
    assert status == 200 and isinstance(results.get("results"), list), "Search failed"
    assert results.get("total", 0) > 0, "Common Tehran query returned no offers"
    for item in results["results"]:
        assert item.get("product", {}).get("id"), "Missing product ID"
        assert item.get("best_offer", {}).get("shop", {}).get("id"), "Missing seller"
    checks.append("catalog-search=ok")

    if active:
        nonce = uuid.uuid4().hex
        payload = {"initial_message": "هدفون", "constraints": {"city": "tehran"},
                   "client_request_id": nonce}
        status, first, _ = fetch(opener, base, "/api/v1/missions/", payload=payload,
                                 timeout=timeout)
        assert status == 201 and first.get("mission_id"), "Mission creation failed"
        status, replay, _ = fetch(opener, base, "/api/v1/missions/", payload=payload,
                                  timeout=timeout)
        assert status == 200 and replay.get("mission_id") == first["mission_id"], (
            "Mission idempotency failed"
        )
        mission_path = f"/api/v1/missions/{first['mission_id']}/"
        status, own, _ = fetch(opener, base, mission_path, timeout=timeout)
        assert status == 200 and own.get("mission_id") == first["mission_id"], (
            "Owner session cannot recover mission"
        )
        outsider = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        status, _, _ = fetch(outsider, base, mission_path, timeout=timeout)
        assert status in (403, 404), "Session ownership isolation failed"
        checks.append("session-ownership-and-create-idempotency=ok")
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Only origin, e.g. https://demo.example.org")
    parser.add_argument("--allow-http-local", action="store_true",
                        help="Allow HTTP only for localhost and 127.0.0.1")
    parser.add_argument("--active", action="store_true",
                        help="Create a DEMO mission and verify session isolation; does not call BoxAPI")
    parser.add_argument("--require-model-configured", action="store_true",
                        help="Require configured model, NOT proof of a live paid provider call")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args(argv)
    try:
        base = validate_base_url(args.base_url, args.allow_http_local)
        if args.timeout <= 0 or args.timeout > 30:
            raise ValueError("Timeout must be between 0 and 30 seconds.")
        checks = perform(base, active=args.active,
                         require_configured=args.require_model_configured,
                         timeout=args.timeout)
    except (AssertionError, ValueError, URLError, OSError) as exc:
        print(f"RELEASE_SMOKE=FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("RELEASE_SMOKE=PASS " + ", ".join(checks))
    print("NOTE: this is not a real BoxAPI call, full seller journey, or mobile device test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
