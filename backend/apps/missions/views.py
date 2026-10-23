"""Mission lifecycle, server-controlled contact actions, and SSE event endpoints."""
from __future__ import annotations

import json
import secrets
from decimal import Decimal
from typing import Any, Iterator

from django.db import transaction
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.agent.graph import _query_from_message, run_purchase_graph
from apps.agent.llm import extract_intent
from apps.agent.conversation import classify_conversation_intent, conversation_reply
from apps.agent.contextual import classify_contextual_turn
from apps.agent.simulator import serialize_contact_attempt, simulate_contact
from apps.agent.contact_evidence import build_contact_evidence
from apps.catalog.models import Offer, Product
from apps.missions.models import ContactAttempt, PurchaseMission
from apps.missions.renderers import ServerSentEventRenderer
from apps.missions.serializers import (
    ContactAttemptCreateSerializer,
    MissionConstraintsSerializer,
    MissionCreateSerializer,
    MissionTurnSerializer,
)
from apps.missions.services import append_events_locked, serialize_mission
from apps.missions.visit_plan import build_visit_plan
from apps.catalog.services.normalization import normalize_persian_text
from apps.search.services import eligible_offer_list, product_search_page, serialize_offer


def _owned_mission(request, mission_id, *, lock=False):
    """Hide even the existence of missions belonging to another browser session."""
    owner = request.session.get("bazaar_owner_token")
    if not isinstance(owner, str) or not owner:
        from django.http import Http404
        raise Http404
    queryset = PurchaseMission.objects.select_for_update() if lock else PurchaseMission.objects
    return get_object_or_404(queryset, pk=mission_id, owner_token=owner)


def _validate_full_constraints(
    existing: dict[str, Any] | None, updates: dict[str, Any] | None
) -> dict[str, Any]:
    merged: dict[str, Any] = {"city": "tehran", "sort": "relevance", **(existing or {})}
    merged.update(updates or {})
    serializer = MissionConstraintsSerializer(data=merged)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    data.setdefault("city", "tehran")
    data.setdefault("sort", "relevance")
    has_lat = "lat" in data
    has_lon = "lon" in data
    if has_lat != has_lon:
        raise ValidationError({"constraints": {"lat": "lat و lon باید با هم ارسال شوند."}})
    if "radius_m" in data and not (has_lat and has_lon):
        raise ValidationError({"constraints": {"radius_m": "برای تعیین شعاع، lat و lon لازم‌اند."}})
    if data.get("sort") == "distance_asc" and not (has_lat and has_lon):
        raise ValidationError({"constraints": {"sort": "مرتب‌سازی فاصله به مختصات مبدأ نیاز دارد."}})
    return data


def _sse_stream(events: list[dict[str, Any]]) -> Iterator[str]:
    for event in events:
        encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        yield f"id: {event['seq']}\ndata: {encoded}\n\n"


def _search_filterset(constraints: dict[str, Any]) -> dict[str, Any]:
    raw_max = constraints.get("max_price_toman")
    return {
        "max_price_toman": Decimal(str(raw_max)) if raw_max not in (None, "") else None,
        "must_have_in_person_credit": bool(constraints.get("must_have_in_person_credit", False)),
        "lat": constraints.get("lat"),
        "lon": constraints.get("lon"),
        "radius_m": constraints.get("radius_m"),
        "sort": constraints.get("sort", "relevance"),
    }


def _serialize_alternatives(mission: PurchaseMission, offer: Offer, shop_id: str) -> list[dict[str, Any]]:
    filters = _search_filterset(mission.constraints or {})
    alternatives = (
        eligible_offer_list(filters, product_id=offer.product_id)
        .exclude(shop_id=shop_id)
        .select_related("shop", "product")[:5]
    )
    return [serialize_offer(candidate, getattr(candidate, "distance_m", None)) for candidate in alternatives]


def _serialize_alternative_products(
    mission: PurchaseMission, product: Product, *, limit: int = 5
) -> list[dict[str, Any]]:
    """Find substitute products in the same category while preserving every hard filter."""
    query = (product.category_name or "").strip()
    if not query:
        query = (product.brand_name or "").strip()
    if not query:
        query = product.persian_title.strip()
    normalized_query = normalize_persian_text(query)
    if len(normalized_query) < 2:
        return []

    search_filters = {
        **_search_filterset(mission.constraints or {}),
        "q": query,
        "normalized_query": normalized_query,
        "page": 1,
        "page_size": min(20, max(limit * 3, 10)),
    }
    payload = product_search_page(search_filters)
    substitutes = [
        result for result in payload.get("results", [])
        if result.get("product", {}).get("id") != product.source_id
    ]
    return substitutes[:limit]


@api_view(["POST"])
def create_mission(request):
    serializer = MissionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    constraints = _validate_full_constraints({}, data.get("constraints", {}))
    if "bazaar_owner_token" not in request.session:
        request.session["bazaar_owner_token"] = secrets.token_hex(24)
    with transaction.atomic():
        mission = PurchaseMission.objects.create(
            initial_message=data["initial_message"],
            owner_token=request.session["bazaar_owner_token"],
            constraints=constraints,
            client_request_id=data.get("client_request_id"),
            status=PurchaseMission.Status.CREATED,
            current_stage="created",
        )
        events = append_events_locked(
            mission,
            [("mission.created", {"status": mission.status, "city": constraints.get("city", "tehran")})],
        )
    return Response({**serialize_mission(mission), "initial_events": events}, status=201)


@api_view(["GET"])
def get_mission(request, mission_id: str):
    mission = _owned_mission(request, mission_id)
    return Response(serialize_mission(mission, include_events=True))


@api_view(["POST"])
@renderer_classes([JSONRenderer, ServerSentEventRenderer])
def mission_turn(request, mission_id: str):
    serializer = MissionTurnSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    created_events: list[dict[str, Any]] = []
    local_intent = classify_conversation_intent(data["message"])
    if local_intent is not None:
        # This API guard is as important as the fast UI guard: mobile or future
        # clients can bypass React. Keep old search state, candidate offers and
        # hard constraints intact, and do not call BoxAPI or the catalogue.
        with transaction.atomic():
            mission = _owned_mission(request, mission_id, lock=True)
            _validate_full_constraints(mission.constraints, data.get("constraints", {}))
            message = conversation_reply(local_intent)
            created_events = append_events_locked(mission, [
                ("user.message", {"message": data["message"]}),
                ("assistant.message", {"text": message}),
                ("turn.completed", {
                    "status": mission.status,
                    "current_stage": mission.current_stage,
                    "intent_parser": "local_conversation",
                    "agent_runtime": "deterministic_guard",
                    "search_query": (mission.state or {}).get("search_query", ""),
                    "constraints": mission.constraints,
                }),
            ])
        response_stream = StreamingHttpResponse(
            _sse_stream(created_events), content_type="text/event-stream; charset=utf-8"
        )
        response_stream["Cache-Control"] = "no-cache, no-transform"
        response_stream["X-Accel-Buffering"] = "no"
        response_stream["X-Mission-ID"] = str(mission.pk)
        return response_stream

    # Do any optional network call before acquiring the mission row lock. A second validation and
    # hard-filter pass happens after locking; model output cannot loosen those constraints.
    initial_mission = _owned_mission(request, mission_id)
    preflight_constraints = _validate_full_constraints(
        initial_mission.constraints, data.get("constraints", {})
    )
    decision = classify_contextual_turn(data["message"], initial_mission.state)
    if (
        decision["kind"] == "refine"
        and decision["constraint_updates"].get("sort") == "distance_asc"
        and preflight_constraints.get("lat") is None
    ):
        decision = {
            "kind": "clarify",
            "reply": "برای مرتب‌سازی فروشگاه‌ها بر اساس نزدیکی، ابتدا موقعیت یا محدوده تهران را انتخاب کن.",
        }
    if decision["kind"] in {"select_product", "explain", "clarify"}:
        # Text-only follow-ups must not trigger paid inference or an unrelated
        # catalogue search. Validate the reference again under the mission lock.
        with transaction.atomic():
            mission = _owned_mission(request, mission_id, lock=True)
            decision = classify_contextual_turn(data["message"], mission.state)
            if (
                decision["kind"] == "refine"
                and decision["constraint_updates"].get("sort") == "distance_asc"
                and preflight_constraints.get("lat") is None
            ):
                decision = {
                    "kind": "clarify",
                    "reply": "برای مرتب‌سازی بر اساس نزدیکی، ابتدا محدوده تهران را انتخاب کن.",
                }
            selected_id = None
            if decision["kind"] == "select_product":
                selected_id = decision["product_id"]
                allowed = selected_id in (mission.state or {}).get("visible_product_ids", [])
                allowed = allowed and selected_id in (mission.state or {}).get("candidate_product_ids", [])
                if allowed:
                    allowed = eligible_offer_list(
                        _search_filterset(mission.constraints or {}), product_id=selected_id
                    ).exists()
                if allowed:
                    product = Product.objects.filter(source_id=selected_id).first()
                    if product:
                        mission.state = {**(mission.state or {}), "selected_product_id": selected_id}
                        mission.current_stage = "product_selected"
                        mission.save(update_fields=["state", "current_stage", "updated_at"])
                        reply = (
                            f"«{product.persian_title or selected_id}» را انتخاب کردی. "
                            "می‌توانی از کارت همین کالا فروشگاه‌های دارای آفر ثبت‌شده را ببینی."
                        )
                    else:
                        selected_id = None
                        reply = "این مدل دیگر در داده‌های معتبر مأموریت پیدا نشد؛ نتایج را دوباره بررسی کن."
                else:
                    selected_id = None
                    reply = "این مدل دیگر با شرایط فعلی مطابقت ندارد؛ فیلترها را بررسی کن."
            elif decision["kind"] == "explain":
                chosen = (mission.state or {}).get("selected_product_id")
                product = Product.objects.filter(source_id=chosen).first() if chosen else None
                if product:
                    reply = (
                        f"«{product.persian_title}» در نتایج عبارت «{(mission.state or {}).get('search_query', '')}» "
                        "دارای آفر ثبت‌شده و مطابق فیلترهای مأموریت بوده است. "
                        "این به معنی موجودی تأییدشده یا برتری قطعی نسبت به مدل‌های دیگر نیست."
                    )
                else:
                    reply = (
                        "این نتیجه از تطبیق متن محصول و آفرهای واجد شرایط با جست‌وجو و فیلترهای تو آمده است؛ "
                        "برای توضیح یک مدل مشخص، آن را انتخاب کن. موجودی واقعی تأیید نشده است."
                    )
            else:
                pending = decision.get("pending_constraints")
                if isinstance(pending, dict) and pending:
                    mission.constraints = _validate_full_constraints(mission.constraints, pending)
                    mission.save(update_fields=["constraints", "updated_at"])
                reply = decision.get("reply", "لطفاً منظورت را دقیق‌تر مشخص کن.")
            created_events = append_events_locked(mission, [
                ("user.message", {"message": data["message"]}),
                ("assistant.message", {"text": reply}),
                ("turn.completed", {
                    "status": mission.status,
                    "current_stage": mission.current_stage,
                    "intent_parser": "contextual",
                    "agent_runtime": "deterministic_guard",
                    "search_query": (mission.state or {}).get("search_query", ""),
                    "selected_product_id": selected_id or (mission.state or {}).get("selected_product_id"),
                    "constraints": mission.constraints,
                }),
            ])
        response_stream = StreamingHttpResponse(
            _sse_stream(created_events), content_type="text/event-stream; charset=utf-8"
        )
        response_stream["Cache-Control"] = "no-cache, no-transform"
        response_stream["X-Accel-Buffering"] = "no"
        response_stream["X-Mission-ID"] = str(mission.pk)
        return response_stream

    if decision["kind"] == "refine":
        # A change such as "بودجه‌م شد دو میلیون" is not a new product query.
        # Keep the last catalogue phrase and recheck all offer-level constraints.
        preflight_constraints = _validate_full_constraints(
            preflight_constraints, decision["constraint_updates"]
        )
        prior_query = decision["query"]
        intent_result = {
            "search_query": prior_query,
            "max_price_toman": preflight_constraints.get("max_price_toman"),
            "must_have_in_person_credit": preflight_constraints.get("must_have_in_person_credit", False),
            "sort": preflight_constraints.get("sort", "relevance"),
        }
    else:
        intent_result = (
            extract_intent(data["message"], preflight_constraints)
            if _query_from_message(data["message"])
            else None
        )

    with transaction.atomic():
        mission = _owned_mission(request, mission_id, lock=True)
        constraints = _validate_full_constraints(mission.constraints, data.get("constraints", {}))
        if decision["kind"] == "refine":
            # Server-owned context is checked again inside the lock.
            locked_decision = classify_contextual_turn(data["message"], mission.state)
            if locked_decision["kind"] != "refine" or locked_decision["query"] != decision["query"]:
                raise ValidationError({"message": "زمینه جست‌وجو تغییر کرده است؛ درخواست را دوباره بررسی کن."})
            constraints = _validate_full_constraints(constraints, locked_decision["constraint_updates"])
        mission.constraints = constraints
        mission.status = PurchaseMission.Status.ACTIVE
        mission.current_stage = "understanding_request"
        mission.save(update_fields=["constraints", "status", "current_stage", "updated_at"])

        graph_state = run_purchase_graph(
            mission_id=str(mission.pk),
            message=decision["query"] if decision["kind"] == "refine" else data["message"],
            constraints=constraints,
            intent_result=intent_result,
            intent_resolved=True,
        )
        if decision["kind"] == "refine":
            graph_state["intent_parser"] = "contextual"
        # Persist constraints inferred from the user's natural-language message (e.g. budget or
        # in-person credit), not only the filter values supplied by the UI. The same effective
        # constraints must be reused for contact validation and alternative generation.
        effective_constraints = _validate_full_constraints(
            constraints, graph_state.get("constraints", constraints)
        )
        mission.constraints = effective_constraints
        response = graph_state.get("search_response", {})
        last_state = dict(mission.state or {})
        new_query = graph_state.get("search_query", "")
        # Visible ordinal references target only the first four cards by default.
        # An expanded list will require explicit UI selection, never a guess.
        visible_products = [
            item.get("product", {}).get("id")
            for item in response.get("results", [])[:4]
            if isinstance(item, dict) and isinstance(item.get("product"), dict)
        ]
        previous_selection = last_state.get("selected_product_id")
        selected_product = (
            previous_selection if previous_selection in graph_state.get("candidate_product_ids", [])
            and new_query == last_state.get("search_query") else None
        )
        mission.state = {
            **{k: v for k, v in last_state.items() if k in {"last_contact_attempt_id", "last_contact_outcome"}},
            "selected_product_id": selected_product,
            "visible_product_ids": visible_products,
            "candidate_product_ids": graph_state.get("candidate_product_ids", []),
            "eligible_offer_ids": graph_state.get("eligible_offer_ids", []),
            "search_query": graph_state.get("search_query", ""),
            "agent_runtime": graph_state.get("graph_runtime", "langgraph"),
            "intent_parser": graph_state.get("intent_parser", "heuristic"),
            "last_turn_message": data["message"],
        }
        mission.status = graph_state.get("status", PurchaseMission.Status.WAITING_FOR_USER)
        mission.current_stage = graph_state.get("current_stage", "results_ready")
        mission.save(update_fields=["constraints", "state", "status", "current_stage", "updated_at"])

        events_to_save: list[tuple[str, dict[str, Any]]] = [
            ("user.message", {"message": data["message"]}),
            ("stage", {"stage": "searching_catalog", "label": "در حال بررسی محصولات و آفرهای تهران"}),
            ("assistant.message", {"text": graph_state.get("assistant_message", "جست‌وجو انجام شد.")}),
            (
                "ui.component",
                {
                    "component": graph_state.get("ui_component", {}).get("type", "empty_state"),
                    "data": graph_state.get("ui_component", {}).get("data", {}),
                },
            ),
            (
                "turn.completed",
                {
                    "status": mission.status,
                    "current_stage": mission.current_stage,
                    "total": response.get("total", 0),
                    "agent_runtime": graph_state.get("graph_runtime", "langgraph"),
                    "intent_parser": graph_state.get("intent_parser", "heuristic"),
                    "search_query": graph_state.get("search_query", ""),
                    "selected_product_id": selected_product,
                    # Sync the *effective* server-side filters to the browser.
                    # Natural-language budget/credit may differ from initial form toggles.
                    "constraints": effective_constraints,
                },
            ),
        ]
        created_events = append_events_locked(mission, events_to_save)

    response_stream = StreamingHttpResponse(
        _sse_stream(created_events), content_type="text/event-stream; charset=utf-8"
    )
    response_stream["Cache-Control"] = "no-cache, no-transform"
    response_stream["X-Accel-Buffering"] = "no"
    response_stream["X-Mission-ID"] = str(mission.pk)
    return response_stream


@api_view(["GET"])
def get_visit_plan(request, mission_id: str):
    mission = _owned_mission(request, mission_id)
    plan = (mission.state or {}).get("visit_plan")
    if not isinstance(plan, dict) or not plan:
        raise NotFound("برنامه مراجعه برای این مأموریت هنوز آماده نیست.")
    return Response(plan)


@api_view(["POST"])
def create_contact_attempt(request, mission_id: str):
    serializer = ContactAttemptCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    request_id = data.get("client_request_id")
    # Serialize contact requests for this mission, including duplicate-key checks.
    with transaction.atomic():
        mission = _owned_mission(request, mission_id, lock=True)
        if request_id:
            existing = ContactAttempt.objects.filter(
                mission=mission, client_request_id=request_id
            ).first()
            if existing is not None:
                if existing.offer_id != data["offer_id"] or existing.shop_id != data["shop_id"]:
                    raise ValidationError({
                        "client_request_id": "این شناسه قبلاً برای استعلام دیگری استفاده شده است."
                    })
                if not existing.response_snapshot:
                    raise ValidationError({
                        "client_request_id": "نتیجه استعلام قبلی هنوز آماده نیست."
                    })
                recorded_questions = existing.response_snapshot.get("attempt", {}).get(
                    "requested_questions", ["stock", "price", "hours"]
                )
                if recorded_questions != data["questions"] or existing.purpose != data["purpose"]:
                    raise ValidationError({
                        "client_request_id": "این شناسه برای سؤال یا نوع استعلام متفاوتی ثبت شده است."
                    })
                return Response(existing.response_snapshot, status=200)
        offer = get_object_or_404(Offer.objects.select_related("shop", "product"), source_id=data["offer_id"])
        if offer.shop_id != data["shop_id"]:
            raise ValidationError({"offer_id": "این آفر متعلق به فروشگاه انتخاب‌شده نیست."})

        # Enforce all hard filters against the current database state immediately before simulation.
        candidate_ids = set((mission.state or {}).get("candidate_product_ids", []))
        if offer.product_id not in candidate_ids:
            raise ValidationError({"offer_id": "ابتدا این محصول را در همین مأموریت جست‌وجو کن."})
        filters = _search_filterset(mission.constraints or {})
        eligible = eligible_offer_list(filters, product_id=offer.product_id).filter(source_id=offer.source_id).exists()
        if not eligible:
            raise ValidationError({"offer_id": "این آفر شرایط الزامی مأموریت را رعایت نمی‌کند."})

        result = simulate_contact(
            mission_id=str(mission.pk),
            shop_id=data["shop_id"],
            offer_id=data["offer_id"],
            purpose=data["purpose"],
            client_request_id=request_id,
        )
        attempt_payload = serialize_contact_attempt(result.attempt)
        attempt_payload["requested_questions"] = data["questions"]
        attempt_payload["evidence"] = build_contact_evidence(
            offer, result.attempt.outcome, data["questions"]
        )
        alternatives: list[dict[str, Any]] = []
        alternative_products: list[dict[str, Any]] = []
        if result.attempt.outcome != "confirmed_available":
            alternatives = _serialize_alternatives(mission, offer, data["shop_id"])
            alternative_products = _serialize_alternative_products(mission, offer.product)

        event_list: list[tuple[str, dict[str, Any]]] = [
            ("contact.completed", {"attempt": attempt_payload, "source_type": "demo_simulation"}),
            (
                "ui.component",
                {
                    "component": "contact_progress",
                    "data": {
                        "attempts": [attempt_payload],
                        "next_action": "compare_alternatives" if (alternatives or alternative_products) else None,
                    },
                },
            ),
        ]
        visit_plan: dict | None = None
        if result.attempt.outcome == "confirmed_available":
            backup_candidates = _serialize_alternatives(mission, offer, data["shop_id"])
            visit_plan = build_visit_plan(
                offer, str(result.attempt.pk),
                backup_candidates[0] if backup_candidates else None,
            )
            event_list.append(("ui.component", {"component": "visit_plan", "data": visit_plan}))
        if alternatives or alternative_products:
            event_list.append(
                (
                    "ui.component",
                    {
                        "component": "alternative_options",
                        "data": {
                            "alternatives": alternatives,
                            "alternative_products": alternative_products,
                            "preserved_constraints": list((mission.constraints or {}).keys()),
                        },
                    },
                )
            )
        with transaction.atomic():
            locked_mission = PurchaseMission.objects.select_for_update().get(pk=mission.pk)
            existing_state = locked_mission.state or {}
            alternative_product_ids = [
                item["product"]["id"]
                for item in alternative_products
                if item.get("product", {}).get("id")
            ]
            candidate_product_ids = list(
                dict.fromkeys([*existing_state.get("candidate_product_ids", []), *alternative_product_ids])
            )
            locked_mission.state = {
                **existing_state,
                "last_contact_attempt_id": str(result.attempt.pk),
                "last_contact_outcome": result.attempt.outcome,
                "alternative_offer_ids": [item["id"] for item in alternatives],
                "alternative_product_ids": alternative_product_ids,
                "candidate_product_ids": candidate_product_ids,
                **({"visit_plan": visit_plan} if visit_plan is not None else {}),
            }
            locked_mission.current_stage = "contact_checked"
            locked_mission.status = PurchaseMission.Status.WAITING_FOR_USER
            locked_mission.save(update_fields=["state", "current_stage", "status", "updated_at"])
            events = append_events_locked(locked_mission, event_list)

        payload = {
            "attempt": attempt_payload,
            "alternatives": alternatives,
            "alternative_products": alternative_products,
            "events": events,
            "mission": serialize_mission(locked_mission),
        }
        # Persist the response before commit so retries return the same event sequence
        # and simulation outcome, even if the client missed the first response.
        result.attempt.response_snapshot = payload
        result.attempt.save(update_fields=["response_snapshot"])
        return Response(payload, status=201)
