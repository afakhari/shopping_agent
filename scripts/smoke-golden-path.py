#!/usr/bin/env python3
"""Run a real HTTP smoke test for Bazaar Compass' chat-first golden path.

Uses only the Python standard library. It creates a local mission and, unless --skip-contact
is supplied, one controlled DEMO_SIMULATION contact attempt. It never makes a real phone call.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


class SmokeFailure(RuntimeError):
    pass


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    accept: str = "application/json",
    timeout: float = 15,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept": accept}
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(base_url.rstrip("/") + path, data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        response_headers = {key.lower(): value for key, value in exc.headers.items()}
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"body": raw[:500]}
        raise SmokeFailure(
            f"HTTP {exc.code} برای {method} {path}: {json.dumps(detail, ensure_ascii=False)}"
        ) from exc
    except URLError as exc:
        raise SmokeFailure(f"اتصال به {base_url} برقرار نشد: {exc.reason}") from exc
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"پاسخ {path} JSON معتبر نیست؛ Content-Type={response_headers.get('content-type')}" ) from exc
    if not isinstance(parsed, dict):
        raise SmokeFailure(f"پاسخ {path} باید یک JSON object باشد.")
    return status, parsed, response_headers


def post_sse(base_url: str, path: str, payload: dict[str, Any], timeout: float = 30) -> tuple[int, list[dict[str, Any]], dict[str, str]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        base_url.rstrip("/") + path,
        data=body,
        method="POST",
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            raw = response.read().decode("utf-8", errors="replace")
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise SmokeFailure(f"ارسال پیام شکست خورد: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise SmokeFailure(f"اتصال هنگام ارسال پیام شکست خورد: {exc.reason}") from exc

    if not content_type.lower().startswith("text/event-stream"):
        raise SmokeFailure(f"Content-Type پاسخ گفتگو باید text/event-stream باشد؛ دریافت شد: {content_type}")

    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        value = line[5:].strip()
        if not value:
            continue
        try:
            event = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("type"), str):
            events.append(event)
    if not events:
        raise SmokeFailure("پاسخ SSE دریافت شد، اما هیچ رویداد JSON قابل‌خواندنی نداشت.")
    return status, events, response_headers


def find_product_results(component_name: str, data: dict[str, Any]) -> list[dict[str, Any]] | None:
    if component_name == "product_results":
        results = data.get("results")
        return results if isinstance(results, list) else None
    if component_name == "component_stack":
        children = data.get("components", [])
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_data = child.get("data")
                if isinstance(child_data, dict):
                    found = find_product_results(str(child.get("type", "")), child_data)
                    if found is not None:
                        return found
    return None


def first_results_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for event in events:
        if event.get("type") != "ui.component":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        data = payload.get("data")
        if not isinstance(data, dict):
            continue
        results = find_product_results(str(payload.get("component", "")), data)
        if results is not None:
            return [item for item in results if isinstance(item, dict)]
    return []


def validate_hard_constraints(results: list[dict[str, Any]], constraints: dict[str, Any]) -> None:
    budget = constraints.get("max_price_toman")
    budget_decimal: Decimal | None = None
    if budget not in (None, ""):
        try:
            budget_decimal = Decimal(str(budget))
        except InvalidOperation as exc:
            raise SmokeFailure(f"سقف بودجهٔ ذخیره‌شده معتبر نیست: {budget!r}") from exc
    needs_credit = bool(constraints.get("must_have_in_person_credit", False))

    for item in results:
        product = item.get("product") or {}
        offer = item.get("best_offer") or {}
        shop = offer.get("shop") or {}
        title = product.get("title", product.get("id", "محصول بدون عنوان"))
        price = offer.get("price_toman")
        if budget_decimal is not None:
            if price is None:
                raise SmokeFailure(f"نتیجهٔ «{title}» با قیمت نامشخص تحت سقف بودجه نمایش داده شده است.")
            try:
                price_decimal = Decimal(str(price))
            except InvalidOperation as exc:
                raise SmokeFailure(f"قیمت نتیجهٔ «{title}» عدد معتبر نیست: {price!r}") from exc
            if price_decimal <= 0 or price_decimal > budget_decimal:
                raise SmokeFailure(f"نقض سقف بودجه برای «{title}»: قیمت {price} / سقف {budget_decimal}")
        if needs_credit and not shop.get("accepts_in_person_credit", False):
            raise SmokeFailure(f"نتیجهٔ «{title}» شرط خرید اعتباری حضوری را رعایت نمی‌کند.")


def classify_llm_runtime(parser_used: str, config_status: str, agent_mode: str) -> tuple[str, str]:
    """Classify the actual turn without inferring configuration from a missing field."""
    if parser_used == "llm":
        return "ACTIVE", "این turn واقعاً با خروجی adapter مدل پردازش شده است."
    if config_status in {"missing_api_key", "missing_model", "disabled", "unsupported_provider", "invalid_base_url"}:
        return "FALLBACK_UNCONFIGURED", f"پیکربندی LLM کامل نیست (reason={config_status})."
    if config_status == "configured" or agent_mode == "model_configured":
        return "FALLBACK_AFTER_CONFIG", "پیکربندی ظاهراً کامل است، اما این turn خروجی معتبر LLM نگرفت؛ لاگ backend را بررسی کن."
    if parser_used == "heuristic":
        return "HEURISTIC_FALLBACK_UNDIAGNOSED", "parser قطعی استفاده شد اما endpoint سلامت تشخیص پیکربندی را گزارش نمی‌کند؛ کد بک‌اند/تصویر Docker را به‌روز کن."
    return "UNKNOWN", f"parser={parser_used}; llm_config={config_status}; agent_mode={agent_mode}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080", help="ریشهٔ فرانت‌اند/پروکسی API")
    parser.add_argument("--query", default="فشارسنج", help="عبارت تست واقعی از دیتاست")
    parser.add_argument("--max-price-toman", default=None, help="سقف بودجه اختیاری به تومان، بدون جداکننده")
    parser.add_argument("--in-person-credit", action="store_true", help="اعمال شرط سخت خرید اعتباری حضوری")
    parser.add_argument("--skip-contact", action="store_true", help="فقط مسیر جست‌وجو را اجرا کن؛ تماس دمو ثبت نکن")
    parser.add_argument("--expect-empty", action="store_true", help="انتظار دارد رابط حالت بدون نتیجه و فرم اصلاح را نمایش دهد")
    parser.add_argument("--require-llm", action="store_true", help="اگر این turn واقعاً با LLM پردازش نشود، کد خروج غیرصفر بده")
    args = parser.parse_args()

    print(f"[1/6] Readiness: {args.base_url}")
    ready_status, ready, _ = request_json(args.base_url, "/api/v1/health/ready/")
    if ready_status != 200 or ready.get("status") != "ready":
        raise SmokeFailure(f"Backend آماده نیست: {ready}")
    agent_mode = str(ready.get("agent_mode", "unknown"))
    llm_diagnostics = ready.get("llm") if isinstance(ready.get("llm"), dict) else {}
    llm_config_status = str(llm_diagnostics.get("status", "unknown"))
    print(f"  PASS database readiness; agent_mode={agent_mode}; llm_config={llm_config_status}")
    if llm_diagnostics:
        print(
            "  LLM config flags: "
            f"enabled={llm_diagnostics.get('enabled', 'unknown')}; "
            f"provider_supported={llm_diagnostics.get('provider_supported', 'unknown')}; "
            f"api_key_present={llm_diagnostics.get('api_key_present', 'unknown')}; "
            f"model_present={llm_diagnostics.get('model_present', 'unknown')}; "
            f"base_url_valid={llm_diagnostics.get('base_url_valid', 'unknown')}"
        )

    print("[2/6] Raw catalog API")
    query_string = urlencode({"q": args.query, "page": 1, "page_size": 3})
    catalog_status, catalog, _ = request_json(args.base_url, f"/api/v1/catalog/search/?{query_string}")
    if catalog_status != 200:
        raise SmokeFailure(f"API کاتالوگ HTTP {catalog_status} برگرداند.")
    print(f"  HTTP {catalog_status}; total={catalog.get('total')}; results_in_page={len(catalog.get('results', []))}")

    constraints: dict[str, Any] = {"city": "tehran", "sort": "relevance"}
    if args.max_price_toman is not None:
        value = args.max_price_toman.strip()
        if not value.isdigit():
            raise SmokeFailure("--max-price-toman باید عدد صحیح تومان، بدون کاما یا جداکننده باشد.")
        constraints["max_price_toman"] = value
    if args.in_person_credit:
        constraints["must_have_in_person_credit"] = True

    print("[3/6] Create mission")
    create_status, created, _ = request_json(
        args.base_url,
        "/api/v1/missions/",
        method="POST",
        payload={"initial_message": args.query, "constraints": constraints},
    )
    if create_status != 201:
        raise SmokeFailure(f"ایجاد مأموریت HTTP {create_status} برگرداند.")
    mission_id = created.get("mission_id")
    if not isinstance(mission_id, str):
        raise SmokeFailure(f"ایجاد مأموریت mission_id برنگرداند: {created}")
    print(f"  PASS mission_id={mission_id}")

    print("[4/6] Chat turn + SSE events")
    turn_status, events, headers = post_sse(
        args.base_url,
        f"/api/v1/missions/{quote(mission_id, safe='')}/turns/",
        {"message": args.query, "constraints": constraints},
    )
    types = [event.get("type") for event in events]
    required_types = {"user.message", "assistant.message", "ui.component", "turn.completed"}
    missing = sorted(required_types - set(types))
    if missing:
        raise SmokeFailure(f"SSE بعضی رویدادهای ضروری را ندارد: {missing}; انواع دریافت‌شده={types}")
    seqs = [event.get("seq") for event in events if isinstance(event.get("seq"), int)]
    if seqs and seqs != sorted(seqs):
        raise SmokeFailure(f"ترتیب seq رویدادهای SSE صعودی نیست: {seqs}")
    completion = next(event for event in reversed(events) if event.get("type") == "turn.completed")
    completion_payload = completion.get("payload") if isinstance(completion.get("payload"), dict) else {}
    parser_used = str(completion_payload.get("intent_parser", "unknown"))
    graph_used = str(completion_payload.get("agent_runtime", "unknown"))
    print(f"  HTTP {turn_status}; content-type={headers.get('content-type')}")
    print(f"  PASS events={len(events)}; runtime={graph_used}; intent_parser={parser_used}")

    print("[5/6] Validate real catalogue results and hard constraints")
    results = first_results_from_events(events)
    _, snapshot, _ = request_json(args.base_url, f"/api/v1/missions/{quote(mission_id, safe='')}/")
    effective_constraints = snapshot.get("constraints", {})
    if args.expect_empty:
        if results:
            raise SmokeFailure(f"در آزمون --expect-empty محصولی برگشت؛ تعداد={len(results)}")
        component_names = {
            str((event.get("payload") or {}).get("component", ""))
            for event in events
            if event.get("type") == "ui.component" and isinstance(event.get("payload"), dict)
        }
        if not component_names.intersection({"empty_state", "clarification_form"}):
            raise SmokeFailure(f"نتیجه خالی بود اما فرم اصلاح/clarification نمایش داده نشد؛ componentها={component_names}")
        print(f"  PASS empty-state UI rendered; components={sorted(component_names)}")
        results = []
    else:
        if not results:
            raise SmokeFailure(
                "جست‌وجوی مأموریت نتیجهٔ محصول نداشت؛ مسیر UI صفرنتیجه/فرم اصلاح باید به کاربر نمایش داده شود. "
                f"برای آزمون مسیر موفق، --query دیگری مثل 'هدفون بی سیم' امتحان کن. mission_id={mission_id}"
            )
        validate_hard_constraints(results, effective_constraints)
        first = results[0]
        product = first.get("product") if isinstance(first.get("product"), dict) else {}
        offer = first.get("best_offer") if isinstance(first.get("best_offer"), dict) else {}
        shop = offer.get("shop") if isinstance(offer.get("shop"), dict) else {}
        print(f"  PASS total_on_page={len(results)}; first_product={product.get('title')}")
        print(f"  first_offer={offer.get('price_toman')} Toman; shop={shop.get('name')}")

    contact_outcome: str | None = None
    if results and not args.skip_contact:
        print("[6/6] Controlled contact simulator (no real call)")
        if not offer.get("id") or not shop.get("id"):
            raise SmokeFailure("آفر اول شناسهٔ محصول/فروشگاه لازم برای شبیه‌سازی استعلام را ندارد.")
        contact_status, contact, _ = request_json(
            args.base_url,
            f"/api/v1/missions/{quote(mission_id, safe='')}/contact-attempts/",
            method="POST",
            payload={"shop_id": shop["id"], "offer_id": offer["id"], "purpose": "verify_availability"},
        )
        if contact_status != 201:
            raise SmokeFailure(f"شبیه‌سازی استعلام HTTP {contact_status} برگرداند.")
        attempt = contact.get("attempt") if isinstance(contact.get("attempt"), dict) else {}
        contact_outcome = str(attempt.get("outcome", "unknown"))
        if attempt.get("source_type") != "demo_simulation":
            raise SmokeFailure("نتیجهٔ استعلام از نوع demo_simulation نیست؛ در این تست هیچ تماس واقعی مجاز نیست.")
        alternative_offers = contact.get("alternatives", [])
        alternative_products = contact.get("alternative_products", [])
        validate_hard_constraints(
            [
                {"product": {"title": f"آفر جایگزین {item.get('id', '')}"}, "best_offer": item}
                for item in alternative_offers if isinstance(item, dict)
            ],
            effective_constraints,
        )
        validate_hard_constraints(
            [item for item in alternative_products if isinstance(item, dict)],
            effective_constraints,
        )
        print(f"  PASS outcome={contact_outcome}; source_type=demo_simulation; alternatives={len(alternative_offers)} offers/{len(alternative_products)} products")
        if contact_outcome == "confirmed_available":
            response_events = contact.get("events", [])
            if not any(
                isinstance(event, dict)
                and event.get("type") == "ui.component"
                and isinstance(event.get("payload"), dict)
                and event["payload"].get("component") == "visit_plan"
                for event in response_events
            ):
                raise SmokeFailure("با تأیید شبیه‌سازی، رویداد رابط visit_plan دریافت نشد.")

    llm_ok = parser_used == "llm"
    llm_runtime, llm_explanation = classify_llm_runtime(parser_used, llm_config_status, agent_mode)
    print(f"LLM_RUNTIME={llm_runtime} ({llm_explanation})")

    print(f"SMOKE_RESULT=PASS; mission_id={mission_id}; llm_used={'yes' if llm_ok else 'no'}; contact={contact_outcome or 'skipped'}")
    if args.require_llm and not llm_ok:
        print("ERROR: --require-llm تعیین شده بود، اما این درخواست با LLM پردازش نشد.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"SMOKE_RESULT=FAIL; {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
