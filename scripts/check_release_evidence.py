#!/usr/bin/env python3
"""Fail closed on unsupported release claims: 20 edge + 12 E2E + 5 owner gates."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


def assess_release(manifest: dict) -> list[str]:
    problems = []
    sha = manifest.get("git_sha")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        problems.append("Missing verified 40-character release SHA")
    url = manifest.get("production_url")
    if not isinstance(url, str) or urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
        problems.append("Missing real HTTPS production URL")
    for name in ("ci_url", "demo_video_url"):
        address = manifest.get(name)
        if not isinstance(address, str) or urlsplit(address).scheme != "https":
            problems.append(f"Missing {name}")
    checks = manifest.get("checks", [])
    ids = [item.get("id") for item in checks if isinstance(item, dict)]
    counts = Counter(item.get("kind") for item in checks if isinstance(item, dict))
    if len(ids) != len(set(ids)) or counts["edge"] != 20 or counts["e2e"] != 12:
        problems.append("Expected 20 unique edge cases and 12 unique E2E journeys")
    for check in checks:
        if not isinstance(check, dict):
            problems.append("Malformed check")
            continue
        if (check.get("result") != "PASS"
                or not check.get("evidence")
                or check.get("sha") != sha
                or not check.get("tested_at")):
            problems.append(f"Unverified: {check.get('id', '?')}")
    gates = manifest.get("other_gates", [])
    expected = {"PROD-HTTPS", "DATASET", "BOXAPI", "MOBILE-A11Y", "SEARCH-GOLD"}
    if {gate.get("id") for gate in gates if isinstance(gate, dict)} != expected:
        problems.append("Missing required owner-controlled production gates")
    for gate in gates:
        if gate.get("result") != "PASS" or not gate.get("evidence"):
            problems.append(f"Unverified release gate: {gate.get('id')}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    status = json.loads(args.manifest.read_text(encoding="utf-8"))
    problems = assess_release(status)
    if problems:
        print(f"RELEASE_GATE=BLOCKED count={len(problems)}")
        for item in problems:
            print(f" - {item}")
        return 1
    print("RELEASE_GATE=PASS. Evidence manifest is complete; independently verify the links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
