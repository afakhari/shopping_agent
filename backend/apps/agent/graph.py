"""LangGraph pipeline for purchase missions, with optional LLM intent extraction.

Catalogue eligibility remains in ordinary Python/Django services. The optional model may interpret
language, but it never generates product facts or bypasses hard purchasing constraints.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, TypedDict

from apps.agent.llm import extract_intent
from apps.catalog.services.normalization import normalize_persian_text
from apps.search.services import product_search_page


STOP_WORDS = {
    # Purchase-intent phrasing and common Persian variants. Keep entries unique so lint
    # catches real maintenance mistakes instead of hiding duplicate tokens in the set.
    "میخوام", "می خواهم", "می خوام", "میخواهم", "می کنم", "میگردم", "می گردم",
    "می‌گردم", "میخواستم", "می", "خواهم", "یه", "یک", "برای", "برام", "به", "از",
    "با", "و", "یا", "در", "رو", "را", "که", "چه", "تا", "سقف", "بودجه",
    "حداکثر", "قیمت", "تومان", "مناسب", "خرید", "بخرم", "بخر", "لطفا", "لطفاً",
    "من", "دنبال", "نیاز", "دارم", "میلیون", "هزار", "امروز", "حضوری", "تهران",
    "فروشگاه", "فروشگاهی",
}
BUDGET_RE = re.compile(
    r"(?:تا\s+(?:سقف\s+)?|حداکثر(?:\s+بودجه)?\s*|سقف\s+بودجه\s+|بودجه\s+)"
    r"(\d+(?:[.,]\d+)?)\s*(میلیون|هزار)?",
)


class MissionGraphState(TypedDict, total=False):
    mission_id: str
    user_message: str
    constraints: dict[str, Any]
    search_query: str
    search_filters: dict[str, Any]
    search_response: dict[str, Any]
    candidate_product_ids: list[str]
    eligible_offer_ids: list[str]
    assistant_message: str
    ui_component: dict[str, Any]
    status: str
    current_stage: str
    error_code: str | None
    intent_parser: str
    intent_result: dict[str, Any] | None
    intent_resolved: bool


def _budget_from_message(message: str) -> str | None:
    normalized = normalize_persian_text(message)
    match = BUDGET_RE.search(normalized)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", "."))
    except InvalidOperation:
        return None
    unit = match.group(2)
    if unit == "میلیون":
        amount *= Decimal(1_000_000)
    elif unit == "هزار":
        amount *= Decimal(1_000)
    if amount < 0 or amount >= Decimal("1e30"):
        return None
    return str(amount.quantize(Decimal("1")))


def _query_from_message(message: str) -> str:
    normalized = normalize_persian_text(message)
    normalized = BUDGET_RE.sub(" ", normalized)
    normalized = re.sub(r"\d+(?:[.,]\d+)?", " ", normalized)
    tokens = []
    for token in normalized.split():
        if token in STOP_WORDS or len(token) < 2:
            continue
        if token not in tokens:
            tokens.append(token)
    # Avoid an excessively broad OR query while preserving a useful phrase in Persian.
    return " ".join(tokens[:6]).strip()


def parse_request_node(state: MissionGraphState) -> dict[str, Any]:
    constraints = dict(state.get("constraints") or {})
    constraints.setdefault("city", "tehran")
    constraints.setdefault("sort", "relevance")
    user_message = state.get("user_message", "")
    normalized_message = normalize_persian_text(user_message)
    if any(phrase in normalized_message for phrase in ("اعتباری", "قسطی", "قسط", "ترب پی")):
        # Explicit natural-language hard intent must not be weakened by an unchecked UI toggle.
        constraints["must_have_in_person_credit"] = True

    # A newly stated budget in the current message supersedes an older filter value.
    heuristic_budget = _budget_from_message(user_message)
    if heuristic_budget:
        constraints["max_price_toman"] = heuristic_budget

    heuristic_query = _query_from_message(user_message)
    # Mission API precomputes this before locking the mission row. Direct callers may omit it.
    # If no product phrase remains after deterministic normalization, ask the user instead of
    # letting the model guess a product from a vague shopping request.
    llm_intent = None if not heuristic_query else (
        state.get("intent_result")
        if state.get("intent_resolved")
        else extract_intent(user_message, constraints)
    )
    if llm_intent is not None:
        search_query = llm_intent["search_query"]
        parser_backend = "llm"
        if not heuristic_budget and not constraints.get("max_price_toman") and llm_intent.get("max_price_toman"):
            constraints["max_price_toman"] = llm_intent["max_price_toman"]
        if llm_intent.get("must_have_in_person_credit"):
            constraints["must_have_in_person_credit"] = True
        # The model may suggest a preference, but a hard credit constraint already present is
        # never removed by the model output.
        if not constraints.get("must_have_in_person_credit"):
            constraints["must_have_in_person_credit"] = False
        llm_sort = llm_intent.get("sort")
        has_origin = constraints.get("lat") is not None and constraints.get("lon") is not None
        if llm_sort in {"relevance", "price_asc", "recent_price_change"} or (
            llm_sort == "distance_asc" and has_origin
        ):
            constraints["sort"] = llm_sort
    else:
        search_query = heuristic_query
        parser_backend = "heuristic"
    filters: dict[str, Any] = {
        "q": search_query,
        "normalized_query": normalize_persian_text(search_query),
        "max_price_toman": (
            Decimal(str(constraints["max_price_toman"]))
            if constraints.get("max_price_toman") not in (None, "") else None
        ),
        "must_have_in_person_credit": bool(constraints.get("must_have_in_person_credit", False)),
        "lat": constraints.get("lat"),
        "lon": constraints.get("lon"),
        "radius_m": constraints.get("radius_m"),
        "sort": constraints.get("sort", "relevance"),
        "page": 1,
        "page_size": 12,
    }
    return {
        "constraints": constraints,
        "search_query": search_query,
        "search_filters": filters,
        "intent_parser": parser_backend,
        "current_stage": "request_parsed",
    }


def search_catalog_node(state: MissionGraphState) -> dict[str, Any]:
    query = state.get("search_query", "")
    if not query:
        response = {"query": "", "page": 1, "page_size": 12, "total": 0, "results": [], "filters": {}}
    elif state.get("constraints", {}).get("city", "tehran") != "tehran":
        response = {"query": query, "page": 1, "page_size": 12, "total": 0, "results": [], "filters": {}}
    else:
        response = product_search_page(state["search_filters"])
    candidate_ids = [row["product"]["id"] for row in response.get("results", [])]
    offer_ids = [row["best_offer"]["id"] for row in response.get("results", [])]
    return {
        "search_response": response,
        "candidate_product_ids": candidate_ids,
        "eligible_offer_ids": offer_ids,
        "current_stage": "catalog_searched",
    }


def _query_form_fields(constraints: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    """Return a small, validated UI schema; the client maps these fields to known controls."""
    return [
        {
            "id": "product_query",
            "label": "چه محصولی می‌خواهی؟",
            "type": "text",
            "required": True,
            "placeholder": "مثلاً فشارسنج پزشکی، هدفون بی‌سیم…",
            "default_value": query,
        },
        {
            "id": "max_price_toman",
            "label": "سقف بودجه (تومان)",
            "type": "number",
            "required": False,
            "min": 1,
            "placeholder": "مثلاً ۳۰۰۰۰۰۰",
            "default_value": str(constraints.get("max_price_toman") or ""),
            "helper_text": "اگر بودجه مهم نیست، خالی بگذار.",
        },
        {
            "id": "must_have_in_person_credit",
            "label": "فقط فروشگاه‌های دارای خرید اعتباری حضوری",
            "type": "checkbox",
            "default_value": bool(constraints.get("must_have_in_person_credit", False)),
        },
        {
            "id": "sort",
            "label": "ترتیب نمایش",
            "type": "select",
            "required": True,
            "default_value": constraints.get("sort", "relevance"),
            "options": [
                {"label": "مرتبط‌ترین", "value": "relevance"},
                {"label": "کمترین قیمت ثبت‌شده", "value": "price_asc"},
                {"label": "تازه‌ترین تغییر قیمت", "value": "recent_price_change"},
            ],
        },
    ]


def render_results_node(state: MissionGraphState) -> dict[str, Any]:
    response = state.get("search_response") or {"results": [], "total": 0}
    count = int(response.get("total", 0))
    query = state.get("search_query", "")
    constraints = dict(state.get("constraints") or {})

    if not query:
        message = "برای شروع، فقط محصول را مشخص کن؛ بودجه و روش خرید را هم می‌توانی همین‌جا تنظیم کنی."
        component = {
            "type": "clarification_form",
            "data": {
                "title": "اول مشخص کنیم دنبال چه کالایی هستی",
                "description": "لازم نیست درخواستت را دوباره در چت توضیح بدهی؛ فیلدهای مرتبط را پر کن.",
                "submit_label": "پیدا کردن گزینه‌ها",
                "purpose": "purchase_search",
                "fields": _query_form_fields(constraints),
            },
        }
        status = "waiting_for_user"
        current_stage = "awaiting_product_details"
    elif count:
        message = f"برای «{query}»، {count} محصول با آفر واجد شرایط پیدا کردم. می‌توانی فروشگاه‌های هر محصول را مقایسه کنی."
        product_component = {"type": "product_results", "data": response}
        # When the catalogue flags a genuinely ambiguous generic term, give the user a one-tap
        # domain switch rather than mixing unrelated categories or asking them to retype it.
        hint = response.get("intent_hint")
        if isinstance(hint, dict) and isinstance(hint.get("alternative_query"), str):
            component = {
                "type": "component_stack",
                "data": {
                    "components": [
                        {
                            "type": "category_choice",
                            "id": "category-scope-choice",
                            "data": {
                                "label": hint.get("label", "حوزه جست‌وجو"),
                                "message": hint.get("message", "این عبارت چند معنی دارد؛ حوزه دیگر را هم می‌توانی ببینی."),
                                "alternative_label": hint.get("alternative_label", "دیدن حوزه دیگر"),
                                "alternative_query": hint.get("alternative_query", ""),
                            },
                        },
                        product_component,
                    ]
                },
            }
        else:
            component = product_component
        status = "waiting_for_user"
        current_stage = "results_ready"
    else:
        message = (
            "با این عبارت و شرایط، محصولی با آفر واجد شرایط پیدا نشد. عبارت یا شرایط را در فرم زیر اصلاح کن؛ "
            "گزینه خارج از شروطت را خودکار نمایش نمی‌دهم."
        )
        component = {
            "type": "empty_state",
            "data": {
                "title": "با این شرایط گزینه منطبقی پیدا نشد",
                "message": "می‌توانی عبارت، سقف بودجه یا شرط خرید اعتباری را تغییر بدهی. هیچ شرط سختی بدون انتخاب تو حذف نمی‌شود.",
                "query": query,
                "purpose": "constraint_adjustment",
                "submit_label": "جست‌وجوی دوباره",
                "fields": _query_form_fields(constraints, query),
            },
        }
        status = "waiting_for_user"
        current_stage = "no_results"
    return {
        "assistant_message": message,
        "ui_component": component,
        "status": status,
        "current_stage": current_stage,
    }


def _build_compiled_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return None
    graph = StateGraph(MissionGraphState)
    graph.add_node("parse_request", parse_request_node)
    graph.add_node("search_catalog", search_catalog_node)
    graph.add_node("render_results", render_results_node)
    graph.add_edge(START, "parse_request")
    graph.add_edge("parse_request", "search_catalog")
    graph.add_edge("search_catalog", "render_results")
    graph.add_edge("render_results", END)
    return graph.compile()


_COMPILED_GRAPH = None
_GRAPH_CHECKED = False


def run_purchase_graph(
    *,
    mission_id: str,
    message: str,
    constraints: dict[str, Any],
    intent_result: dict[str, Any] | None = None,
    intent_resolved: bool = False,
) -> MissionGraphState:
    """Run LangGraph, with deterministic fallback; accept precomputed intent to avoid DB locks during I/O."""
    global _COMPILED_GRAPH, _GRAPH_CHECKED
    if not _GRAPH_CHECKED:
        _COMPILED_GRAPH = _build_compiled_graph()
        _GRAPH_CHECKED = True
    initial: MissionGraphState = {
        "mission_id": mission_id,
        "user_message": message,
        "constraints": constraints,
        "intent_result": intent_result,
        "intent_resolved": intent_resolved,
        "current_stage": "started",
    }
    if _COMPILED_GRAPH is not None:
        result = _COMPILED_GRAPH.invoke(initial)
        result["graph_runtime"] = "langgraph"
        return result
    state: MissionGraphState = dict(initial)
    state.update(parse_request_node(state))
    state.update(search_catalog_node(state))
    state.update(render_results_node(state))
    state["graph_runtime"] = "deterministic_fallback"
    return state
