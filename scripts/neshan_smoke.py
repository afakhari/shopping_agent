#!/usr/bin/env python3
"""Safe one-request Neshan connectivity smoke test, OFFLINE unless explicitly authorized.

Usage:
  python scripts/neshan_smoke.py
  NESHAN_ROUTING_API_KEY=... python scripts/neshan_smoke.py --live --authorize-one-call

Never pass secrets as CLI arguments. Never run LIVE mode in CI or a public demo.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-first one-call Neshan smoke test")
    parser.add_argument("--service", choices=("matrix", "direction"), default="matrix",
                        help="One Neshan REST operation per explicit live invocation")
    parser.add_argument("--live", action="store_true",
                        help="Contact Neshan (potentially billable) exactly once")
    parser.add_argument("--authorize-one-call", action="store_true",
                        help="Explicitly approve the possibility of one charge")
    args = parser.parse_args()
    key = os.environ.get("NESHAN_ROUTING_API_KEY", "").strip()
    if not args.live:
        print("DRY_RUN=PASS; NESHAN_REQUESTS=0; key_configured=" + str(bool(key)).lower())
        print("Live connectivity and provider quota NOT validated.")
        return 0
    if not args.authorize_one_call:
        parser.error("A billable call needs both --live and --authorize-one-call")
    if not key:
        parser.error("NESHAN_ROUTING_API_KEY must be set only in the private environment")
    # Fixed representative Tehran points; no geolocation, merchant name or private user data.
    if args.service == "direction":
        base = "https://api.neshan.org/v4/direction"
        params = urlencode({
            "type": "car", "origin": "35.700100,51.400100",
            "destination": "35.702000,51.402000",
            "alternative": "false",
        })
    else:
        base = "https://api.neshan.org/v1/distance-matrix"
        params = urlencode({
            "type": "car", "origins": "35.700100,51.400100",
            "destinations": "35.702000,51.402000",
        })
    request = Request(
        base + "?" + params,
        headers={"Api-Key": key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with build_opener(HTTPSHandler(), NoRedirects()).open(request, timeout=5) as response:
            status = response.status
            content = response.read(24001)
    except HTTPError as error:
        print("LIVE_RESULT=HTTP_ERROR; http_status=" + str(error.code))
        return 2
    except OSError:
        print("LIVE_RESULT=NETWORK_OR_TLS_FAILURE (credentials and headers hidden)")
        return 2
    if status != 200 or len(content) > 24000:
        print("LIVE_RESULT=BAD_HTTP_OR_BODY_SIZE; http_status=" + str(status))
        return 2
    try:
        data = json.loads(content)
        if args.service == "direction":
            element = data["routes"][0]["legs"][0]
            result = overall = "Ok"
        else:
            element = data["rows"][0]["elements"][0]
            result = element["status"]
            overall = data["status"]
    except (ValueError, LookupError, TypeError):
        print("LIVE_RESULT=UNEXPECTED_JSON")
        return 2
    if overall != "Ok" or result != "Ok":
        print("LIVE_RESULT=NO_VALID_ETA; provider_status=" + str(overall)[:40]
              + "; element_status=" + str(result)[:40])
        return 2
    duration = element.get("duration", {}).get("value")
    distance = element.get("distance", {}).get("value")
    if not isinstance(duration, (int, float)) or not isinstance(distance, (int, float)):
        print("LIVE_RESULT=INVALID_NUMERIC_FIELDS")
        return 2
    print("LIVE_RESULT=PASS; NESHAN_REQUESTS=1; service=" + args.service + "; result=Ok")
    print("duration_seconds=" + str(duration) + "; route_distance_meters=" + str(distance))
    print("These are live provider estimates for fixed DEMO coordinates, not stock or shop verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
