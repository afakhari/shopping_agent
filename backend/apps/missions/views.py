"""Mission lifecycle, server-controlled contact actions, and SSE event endpoints."""
from __future__ import annotations

import json
import secrets
import uuid
from decimal import Decimal
from typing import Any, Iterator

from django.db import transaction
from django.utils import timezone
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
from apps.agent.comparison import build_evidence_comparison
from apps.agent.simulator import serialize_contact_attempt, simulate_contact
from apps.agent.contact_evidence import build_contact_evidence
from apps.catalog.models import Offer, Product
from apps.missions.models import ContactAttempt, MissionEvent, PurchaseMission, RoutingDailyUsage
from apps.missions.renderers import ServerSentEventRenderer
from apps.missions.serializers import (
    ContactAttemptCreateSerializer,
    MissionConstraintsSerializer,
    MissionCreateSerializer,
    MissionTurnSerializer,
    MissionFocusSerializer,
    RouteEstimatesSerializer,
)
from apps.missions.services import append_events_locked, serialize_mission
from apps.missions.visit_plan import build_visit_plan
from apps.missions.neshan_routing import (
    RoutingUnavailable, neshan_enabled, neshan_direction_enabled,
    read_matrix, read_direction, safe_response, successful_response,
    successful_direction_response,
)
from django.conf import settings
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
    # A paired null is the explicit location-clear command. Omission retains the geofence.
    if updates and "lat" in updates and "lon" in updates and updates["lat"] is None and updates["lon"] is None:
        for key in ("lat", "lon", "radius_m"):
            merged.pop(key, None)
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


def _replay_turn_if_completed(mission: PurchaseMission, data: dict[str, Any]):
    """Replay an earlier completed turn by request key without repeating server-side effects."""
    request_id = data.get("client_request_id")
    if not request_id:
        return None
    completed = MissionEvent.objects.filter(
        mission=mission, event_type="turn.completed",
        payload__client_request_id=request_id,
    ).order_by("-seq").first()
    if completed is None:
        return None
    started = MissionEvent.objects.filter(
        mission=mission, event_type="user.message", seq__lt=completed.seq,
    ).order_by("-seq").first()
    if started is None or started.payload.get("message") != data["message"]:
        raise ValidationError({"client_request_id": "این شناسه قبلاً برای پیام دیگری استفاده شده است."})
    saved = MissionEvent.objects.filter(
        mission=mission, seq__gte=started.seq, seq__lte=completed.seq,
    ).order_by("seq")
    events = [
        {"schema_version": 1, "mission_id": str(mission.pk), "seq": event.seq,
         "type": event.event_type, "payload": event.payload}
        for event in saved
    ]
    response = StreamingHttpResponse(
        _sse_stream(events), content_type="text/event-stream; charset=utf-8"
    )
    response["Cache-Control"] = "no-cache, no-transform"
    response["X-Accel-Buffering"] = "no"
    response["X-Mission-ID"] = str(mission.pk)
    return response


def _search_filterset(constraints: dict[str, Any]) -> dict[str, Any]:
    raw_max = constraints.get("max_price_toman")
    return {
        "max_price_toman": Decimal(str(raw_max)) if raw_max not in (None, "") else None,
        "must_have_in_person_credit": bool(constraints.get("must_have_in_person_credit", False)),
        "brand_name": constraints.get("brand_name"),
        "model_exact": constraints.get("model_exact"),
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
    # Repeat response is read before any optional model call or catalog search.
    previous = _replay_turn_if_completed(_owned_mission(request, mission_id), data)
    if previous is not None:
        return previous
    created_events: list[dict[str, Any]] = []
    local_intent = classify_conversation_intent(data["message"])
    if local_intent is not None:
        # This API guard is as important as the fast UI guard: mobile or future
        # clients can bypass React. Keep old search state, candidate offers and
        # hard constraints intact, and do not call BoxAPI or the catalogue.
        with transaction.atomic():
            mission = _owned_mission(request, mission_id, lock=True)
            previous = _replay_turn_if_completed(mission, data)
            if previous is not None:
                return previous
            _validate_full_constraints(mission.constraints, data.get("constraints", {}))
            message = conversation_reply(local_intent)
            created_events = append_events_locked(mission, [
                ("user.message", {"message": data["message"]}),
                ("assistant.message", {"text": message}),
                ("turn.completed", {
                    "status": mission.status,
                    "current_stage": mission.current_stage,
                    "intent_parser": "local_conversation",
                    "client_request_id": data.get("client_request_id"),
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
            "kind": "location_clarify",
            "reply": "برای مرتب‌سازی فروشگاه‌ها بر اساس نزدیکی، ابتدا موقعیت یا محدوده تهران را انتخاب کن.",
        }
    if decision["kind"] in {"select_product", "explore_sellers", "contact_prompt", "compare", "select_offer", "seller_details", "seller_recovery", "explain", "clarify", "location_clarify"}:
        # No extra LLM call for a grounded contextual turn. Re-evaluate every
        # selection with the *effective* constraints inside the row lock.
        with transaction.atomic():
            mission = _owned_mission(request, mission_id, lock=True)
            previous = _replay_turn_if_completed(mission, data)
            if previous is not None:
                return previous
            decision = classify_contextual_turn(data["message"], mission.state)
            if decision["kind"] == "refine" and decision["constraint_updates"].get("sort") == "distance_asc" and preflight_constraints.get("lat") is None:
                decision = {"kind": "location_clarify", "reply": "برای نزدیکی، ابتدا محدوده تهران را انتخاب کن."}
            submitted = data.get("constraints", {})
            if submitted:
                updated = _validate_full_constraints(mission.constraints, submitted)
                if updated != mission.constraints:
                    mission.constraints = updated
                    invalidated = dict(mission.state or {})
                    invalidated.pop("visit_plan", None)
                    invalidated.update(
                        results_stale=True, selected_product_id=None,
                        selected_offer_id=None, selected_shop_id=None,
                        active_surface="products", visible_offer_ids=[],
                    )
                    mission.state = invalidated
                    mission.save(update_fields=["constraints", "state", "updated_at"])
            selected_id = None
            extra_ui = None
            if decision["kind"] in {"select_product", "explore_sellers"}:
                selected_id = decision["product_id"]
                state = mission.state or {}
                # A product picked from "more results" is still an explicit,
                # valid server focus even if not in the first four ordinal IDs.
                allowed = (
                    selected_id == state.get("selected_product_id")
                    if decision["kind"] == "explore_sellers"
                    else selected_id in state.get("visible_product_ids", [])
                )
                allowed = allowed and selected_id in state.get("candidate_product_ids", [])
                allowed = allowed and not state.get("results_stale", False)
                if allowed:
                    allowed = eligible_offer_list(
                        _search_filterset(mission.constraints or {}), product_id=selected_id
                    ).exists()
                if allowed:
                    product = Product.objects.filter(source_id=selected_id).first()
                    if product:
                        mission.state = {**state, "selected_product_id": selected_id}
                        mission.current_stage = "product_selected"
                        reply = (f"«{product.persian_title or selected_id}» انتخاب شد. "
                                 "آفر ثبت‌شده به معنی موجودی تأییدشده نیست.")
                        if decision.get("explore_sellers") or decision["kind"] == "explore_sellers":
                            from apps.search.services import offer_ordering
                            filters = _search_filterset(mission.constraints or {})
                            if decision.get("prefer_distance") and filters.get("lat") is not None:
                                filters["sort"] = "distance_asc"
                            offers = [
                                serialize_offer(o, getattr(o, "distance_m", None))
                                for o in eligible_offer_list(filters, product_id=selected_id).order_by(
                                    *offer_ordering(filters["sort"], filters.get("lat") is not None)
                                )[:5]
                            ]
                            mission.state = {
                                **mission.state, "active_surface": "sellers",
                                "visible_offer_ids": [o["id"] for o in offers],
                            }
                            extra_ui = ("seller_options", {"offers": offers, "product_id": selected_id})
                            if decision.get("prefer_distance") and filters.get("lat") is None:
                                reply += " برای مرتب‌سازی براساس فاصله، موقعیت یا محدوده تهران را انتخاب کن. فهرست زیر بر اساس داده ثبت‌شده است."
                            else:
                                reply += " فروشندگان واجد شرایط این مدل در ادامه آمده‌اند."
                        mission.save(update_fields=["state", "current_stage", "updated_at"])
                    else:
                        selected_id = None
                        reply = "محصول انتخاب‌شده در دیتاست پیدا نشد. نتایج را تازه کن."
                else:
                    selected_id = None
                    reply = "این نتیجه یا فیلترهای آن تغییر کرده‌اند؛ قبل از انتخاب، جست‌وجو را به‌روز کن."
            elif decision["kind"] == "compare":
                state = mission.state or {}
                ids = state.get("compared_product_ids", [])
                if state.get("results_stale"):
                    reply = "نتایج مقایسه قدیمی‌اند؛ ابتدا جست‌وجو را به‌روز کن."
                else:
                    payload = build_evidence_comparison(ids, _search_filterset(mission.constraints or {}))
                    if payload is None:
                        reply = "دو یا سه مدل دارای آفر معتبر را انتخاب کن؛ بدون شواهد مقایسه نمی‌سازم."
                    else:
                        reply = "مقایسهٔ داده‌های ثبت‌شده آماده است. مشخصات ثبت‌نشده نشان‌دهنده یکسانی مدل‌ها نیست."
                        extra_ui = ("comparison_table", payload)
            elif decision["kind"] == "contact_prompt":
                state = mission.state or {}
                offer_id = decision["offer_id"]
                if state.get("results_stale") or offer_id != state.get("selected_offer_id"):
                    reply = "این فروشنده دیگر انتخاب معتبر جاری نیست؛ از فهرست فروشنده‌های همین محصول انتخاب کن."
                else:
                    offer = eligible_offer_list(
                        _search_filterset(mission.constraints or {})
                    ).filter(source_id=offer_id).select_related("shop", "product").first()
                    if offer is None:
                        reply = "آفر فروشنده با شروط فعلی خرید مطابق نیست؛ نتایج را تازه کن."
                    else:
                        reply = (
                            f"برای «{offer.product.persian_title}» از «{offer.shop.name}» "
                            "می‌توانم فقط یک بررسی شبیه‌سازی‌شده اجرا کنم. "
                            "هیچ تماس واقعی با فروشگاه انجام نمی‌شود و موجودی حضوری تأیید نمی‌شود. "
                            "فقط با انتخاب دکمهٔ تأیید، شبیه‌ساز اجرا خواهد شد."
                        )
                        extra_ui = ("contact_prompt", {
                            "offer_id": offer.source_id,
                            "shop_id": offer.shop_id,
                            "shop_name": offer.shop.name,
                            "product_id": offer.product_id,
                            "product_title": offer.product.persian_title,
                            "source_type": "demo_simulation",
                        })
            elif decision["kind"] in {"select_offer", "seller_details"}:
                offer_id = decision["offer_id"]
                state = mission.state or {}
                if state.get("results_stale") or (
                    offer_id not in state.get("visible_offer_ids", [])
                    and offer_id != state.get("selected_offer_id")
                ):
                    reply = "این فروشنده در فهرست معتبر فعلی نیست؛ فروشنده‌ها را تازه کن."
                else:
                    offer = eligible_offer_list(
                        _search_filterset(mission.constraints or {})
                    ).filter(source_id=offer_id).select_related("shop", "product").first()
                    if offer is None:
                        reply = "آفر فروشنده دیگر با شروط خرید مطابقت ندارد."
                    else:
                        mission.state = {**state, "selected_offer_id": offer_id,
                                         "selected_shop_id": offer.shop_id, "active_surface": "sellers"}
                        mission.save(update_fields=["state", "updated_at"])
                        if decision["kind"] == "select_offer":
                            reply = (f"فروشگاه «{offer.shop.name}» برای «{offer.product.persian_title}» انتخاب شد. "
                                     "موجودی و قیمت فعلی به‌صورت واقعی تأیید نشده‌اند.")
                        else:
                            from apps.catalog.services.visit_context import opening_status
                            hours = opening_status(offer.shop.weekly_hours)
                            price = f"{offer.price_toman:,.0f} تومان" if offer.price_toman is not None else "نامشخص"
                            reply = (
                                f"«{offer.shop.name}»؛ نشانی ثبت‌شده: "
                                f"{offer.shop.address or offer.shop.location_label or 'نامشخص'}. "
                                f"ساعات طبق داده ثبت‌شده: {hours.get('label', 'نامشخص')}. "
                                f"قیمت ثبت‌شده: {price}. موجودی واقعی مشخص نیست."
                            )
                            extra_ui = ("seller_details", {"offer": serialize_offer(offer)})
            elif decision["kind"] == "seller_recovery":
                state = mission.state or {}
                offer_id = decision["offer_id"]
                if offer_id != state.get("selected_offer_id") or state.get("results_stale"):
                    reply = "انتخاب فروشنده دیگر معتبر نیست؛ فهرست را به‌روز کن."
                else:
                    original = eligible_offer_list(
                        _search_filterset(mission.constraints or {})
                    ).filter(source_id=offer_id).first()
                    if original is None:
                        reply = "آفر اولیه دیگر با شروط فعلی منطبق نیست؛ جست‌وجو را تازه کن."
                    else:
                        backup = _serialize_alternatives(mission, original, original.shop_id)
                        if backup:
                            extra_ui = ("seller_options", {
                                "offers": backup, "product_id": original.product_id,
                            })
                            mission.state = {
                                **state, "visible_offer_ids": [x["id"] for x in backup],
                                "selected_offer_id": None, "selected_shop_id": None,
                                "active_surface": "sellers", "visit_plan": None,
                            }
                            mission.save(update_fields=["state", "updated_at"])
                            reply = (
                                "طبق گزارشی که دادی، فروشندهٔ قبلی مناسب مراجعه نیست. "
                                "این فروشگاه‌های جایگزین همان محصول را با شروط ثبت‌شده عرضه کرده‌اند؛ "
                                "موجودی هیچ‌کدام در دنیای واقعی تأیید نشده است."
                            )
                        else:
                            reply = "با شروط فعلی، فروشندهٔ جایگزین برای این مدل در دیتاست پیدا نشد. فقط با تغییر صریح شروط می‌توان جست‌وجو را گسترش داد."
            elif decision["kind"] == "explain":
                chosen = (mission.state or {}).get("selected_product_id")
                product = Product.objects.filter(source_id=chosen).first() if chosen else None
                if product is None:
                    reply = "کدام مدل را می‌گویی؟ از کارت محصول آن را انتخاب کن تا دلایل ثبت‌شده را توضیح بدهم."
                else:
                    offer = eligible_offer_list(
                        _search_filterset(mission.constraints or {}), product_id=product.source_id
                    ).first()
                    if offer is None:
                        reply = "این محصول با شروط فعلی آفر منطبق ندارد. ابتدا نتایج را تازه کن."
                    else:
                        facts = [f"در نتایج «{(mission.state or {}).get('search_query', '')}» آفر ثبت‌شده دارد"]
                        if product.brand_name:
                            facts.append(f"برند ثبت‌شده: {product.brand_name}")
                        if product.model:
                            facts.append(f"مدل ثبت‌شده: {product.model}")
                        if offer.price_toman is not None:
                            facts.append(f"قیمت یک آفر واجد شرایط: {offer.price_toman:,.0f} تومان")
                        if mission.constraints.get("must_have_in_person_credit"):
                            facts.append("شرط اعتبار حضوری همین آفر رعایت شده است")
                        reply = f"«{product.persian_title}»: " + "؛ ".join(facts[:4]) + ". برتری قطعی یا موجودی زنده از این داده نتیجه نمی‌شود."
            else:
                if decision["kind"] == "location_clarify":
                    extra_ui = ("location_choice", {
                        "city": "tehran",
                        "source_type": "approximate_region",
                    })
                pending = decision.get("pending_constraints")
                if isinstance(pending, dict) and pending:
                    mission.constraints = _validate_full_constraints(mission.constraints, pending)
                    mission.state = {**(mission.state or {}), "results_stale": bool(
                        (mission.state or {}).get("candidate_product_ids")
                    )}
                    mission.save(update_fields=["constraints", "state", "updated_at"])
                reply = decision.get("reply", "لطفاً منظورت را دقیق‌تر مشخص کن.")
            scoped_events = [
                ("user.message", {"message": data["message"]}),
                ("assistant.message", {"text": reply}),
            ]
            if extra_ui is not None:
                scoped_events.append(("ui.component", {"component": extra_ui[0], "data": extra_ui[1]}))
            scoped_events.append(("turn.completed", {
                "status": mission.status,
                "current_stage": mission.current_stage,
                "intent_parser": "contextual",
                "client_request_id": data.get("client_request_id"),
                "agent_runtime": "deterministic_guard",
                "search_query": (mission.state or {}).get("search_query", ""),
                "selected_product_id": (mission.state or {}).get("selected_product_id"),
                "selected_offer_id": (mission.state or {}).get("selected_offer_id"),
                "result_set_id": (mission.state or {}).get("result_set_id"),
                "results_stale": bool((mission.state or {}).get("results_stale", False)),
                "constraints": mission.constraints,
            }))
            created_events = append_events_locked(mission, scoped_events)
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
        previous = _replay_turn_if_completed(mission, data)
        if previous is not None:
            return previous
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
        result_set_id = uuid.uuid4().hex
        mission.state = {
            **{k: v for k, v in last_state.items() if k in {"last_contact_attempt_id", "last_contact_outcome", "neshan_route_calls"}},
            "result_set_id": result_set_id,
            "results_stale": False,
            "active_surface": "products",
            "visible_offer_ids": [],
            "selected_offer_id": None,
            "selected_shop_id": None,
            "compared_product_ids": [],
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
                    "client_request_id": data.get("client_request_id"),
                    "search_query": graph_state.get("search_query", ""),
                    "selected_product_id": selected_product,
                    "result_set_id": result_set_id,
                    "results_stale": False,
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


@api_view(["POST"])
def mission_focus(request, mission_id: str):
    """Update active UI reference with a server-checked, versioned focus action."""
    serializer = MissionFocusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    with transaction.atomic():
        mission = _owned_mission(request, mission_id, lock=True)
        state = dict(mission.state or {})
        if state.get("result_set_id") != data["result_set_id"] or state.get("results_stale"):
            raise ValidationError({"result_set_id": "این نتایج دیگر معتبر نیستند؛ جست‌وجو را به‌روز کن."})
        action = data["action"]
        filters = _search_filterset(mission.constraints or {})
        if action == "set_compare":
            compared = data["product_ids"]
            if any(pid not in state.get("candidate_product_ids", []) for pid in compared):
                raise ValidationError({"product_ids": "یکی از مدل‌ها در نتایج معتبر جاری نیست."})
            if any(not eligible_offer_list(filters, product_id=pid).exists() for pid in compared):
                raise ValidationError({"product_ids": "یکی از مدل‌ها دیگر آفر مطابق شروط ندارد."})
            state["compared_product_ids"] = compared
        elif action in {"select_product", "view_sellers"}:
            product_id = data["product_id"]
            if product_id not in state.get("candidate_product_ids", []):
                raise ValidationError({"product_id": "محصول در نتایج فعلی مأموریت وجود ندارد."})
            if not eligible_offer_list(filters, product_id=product_id).exists():
                raise ValidationError({"product_id": "این کالا با شرایط فعلی مطابقت ندارد."})
            state["selected_product_id"] = product_id
            if action == "view_sellers":
                offer_ids = data["offer_ids"]
                eligible_ids = set(
                    eligible_offer_list(filters, product_id=product_id).filter(
                        source_id__in=offer_ids
                    ).values_list("source_id", flat=True)
                )
                if eligible_ids != set(offer_ids):
                    raise ValidationError({"offer_ids": "فهرست فروشندگان با شروط فعلی مطابقت ندارد."})
                state.update(active_surface="sellers", visible_offer_ids=offer_ids,
                             selected_offer_id=None, selected_shop_id=None)
            else:
                state.update(active_surface="products", visible_offer_ids=[],
                             selected_offer_id=None, selected_shop_id=None)
        elif action == "view_products":
            state.update(active_surface="products", visible_offer_ids=[],
                         selected_offer_id=None, selected_shop_id=None)
        elif action == "select_offer":
            offer_id = data["offer_id"]
            if offer_id not in state.get("visible_offer_ids", []):
                raise ValidationError({"offer_id": "فروشنده در فهرست فعال نیست."})
            offer = eligible_offer_list(filters).filter(source_id=offer_id).first()
            if offer is None or offer.product_id != state.get("selected_product_id"):
                raise ValidationError({"offer_id": "این آفر دیگر با شروط مأموریت مطابقت ندارد."})
            state.update(active_surface="sellers", selected_offer_id=offer_id,
                         selected_shop_id=offer.shop_id)
        # A visit plan is evidence tied to a particular active selection.
        if action in {"select_product", "view_sellers", "view_products", "select_offer"}:
            state.pop("visit_plan", None)
        if state == (mission.state or {}):
            return Response({
                "state": mission.state, "last_event_seq": mission.last_event_seq,
                "events": [],
            })
        mission.state = state
        mission.save(update_fields=["state", "updated_at"])
        events = append_events_locked(mission, [("focus.updated", {
            "active_surface": state.get("active_surface", "products"),
            "selected_product_id": state.get("selected_product_id"),
            "selected_offer_id": state.get("selected_offer_id"),
            "compared_product_ids": state.get("compared_product_ids", []),
            "result_set_id": state["result_set_id"],
        })])
    return Response({"state": mission.state, "last_event_seq": mission.last_event_seq,
                     "events": events})


@api_view(["GET", "POST"])
def route_estimates(request, mission_id: str):
    """Optional paid ETA; only for eligible, visible sellers on user request."""
    mission = _owned_mission(request, mission_id)
    if request.method == "GET":
        enabled = neshan_enabled()
        return Response({"provider": "neshan", "enabled": enabled,
                         "direction_enabled": neshan_direction_enabled(),
                         "modes": ["car", "motorcycle"] if enabled else []})

    serializer = RouteEstimatesSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    state = mission.state or {}
    if state.get("results_stale") or state.get("result_set_id") != data["result_set_id"]:
        raise ValidationError({"result_set_id": "این فهرست دیگر معتبر نیست؛ ابتدا نتایج را تازه کن."})
    if state.get("active_surface") != "sellers":
        raise ValidationError({"offer_ids": "برای مسیر، ابتدا فهرست فروشنده‌های همان مدل را باز کن."})
    ids = data["offer_ids"]
    if any(offer_id not in state.get("visible_offer_ids", []) for offer_id in ids):
        raise ValidationError({"offer_ids": "فروشنده انتخابی در فهرست معتبر این مأموریت نیست."})
    origin = data["origin"]
    if origin["source"] == "manual_region":
        saved = mission.constraints or {}
        if (
            saved.get("lat") is None or saved.get("lon") is None
            or abs(saved["lat"] - origin["lat"]) > 0.00001
            or abs(saved["lon"] - origin["lon"]) > 0.00001
        ):
            raise ValidationError({"origin": "منطقه مبدأ باید از انتخاب ثبت‌شده در همین مأموریت باشد."})
    filters = _search_filterset(mission.constraints or {})
    selected_id = state.get("selected_product_id")
    if not isinstance(selected_id, str) or not selected_id:
        raise ValidationError({"offer_ids": "ابتدا یک محصول دارای آفر معتبر انتخاب کن."})
    valid = eligible_offer_list(filters, product_id=selected_id).filter(
        source_id__in=ids
    ).select_related("shop", "product")
    by_id = {offer.source_id: offer for offer in valid}
    if len(by_id) != len(ids):
        raise ValidationError({"offer_ids": "یک یا چند آفر با شرط‌های جاری مطابقت ندارند."})
    offers = [by_id[offer_id] for offer_id in ids]
    if len({offer.shop_id for offer in offers}) != len(offers):
        raise ValidationError({"offer_ids": "آفرهای تکراری از یک فروشگاه هزینه مسیر غیرضروری دارند."})
    for offer in offers:
        if (
            offer.shop.lat is None or offer.shop.lon is None
            or not (35.35 <= offer.shop.lat <= 35.95)
            or not (50.9 <= offer.shop.lon <= 51.85)
        ):
            raise ValidationError({"offer_ids": "مختصات همه فروشندگان باید در محدوده داده تهران معتبر باشد."})

    mode = data["mode"]
    service = data["service"]
    if not neshan_enabled() or (service == "direction" and not neshan_direction_enabled()):
        return Response(safe_response(mode=mode))

    # DB row lock enforces per-mission cap across workers. A global paid-call
    # limit at the deployment gateway is still required to enable service.
    with transaction.atomic():
        locked = _owned_mission(request, mission_id, lock=True)
        locked_state = dict(locked.state or {})
        if (
            locked_state.get("result_set_id") != data["result_set_id"]
            or locked_state.get("results_stale")
            or locked_state.get("visible_offer_ids") != state.get("visible_offer_ids")
        ):
            raise ValidationError({"result_set_id": "فهرست حین درخواست تغییر کرد؛ دوباره بررسی کن."})
        used = int(locked_state.get("neshan_route_calls", 0))
        if used >= settings.NESHAN_ROUTING_MAX_CALLS_PER_MISSION:
            return Response(safe_response(mode=mode, reason="mission_budget_exhausted"))
        daily, _ = RoutingDailyUsage.objects.select_for_update().get_or_create(
            day=timezone.localdate()
        )
        if daily.requests >= settings.NESHAN_ROUTING_DAILY_MAX_CALLS:
            return Response(safe_response(mode=mode, reason="daily_budget_exhausted"))
        daily.requests += 1
        daily.save(update_fields=["requests"])
        locked_state["neshan_route_calls"] = used + 1
        locked.state = locked_state
        locked.save(update_fields=["state", "updated_at"])
    try:
        if service == "direction":
            only = offers[0]
            result = read_direction(
                (origin["lat"], origin["lon"]),
                (only.shop.lat, only.shop.lon),
                mode,
            )
            return Response(successful_direction_response(
                mode=mode, offer_id=only.source_id, route=result,
            ))
        matrix = read_matrix(
            (origin["lat"], origin["lon"]),
            [(offer.shop.lat, offer.shop.lon) for offer in offers],
            mode,
        )
    except RoutingUnavailable as error:
        return Response(safe_response(mode=mode, reason=error.reason))
    return Response(successful_response(mode=mode, offers=offers, matrix=matrix))


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
        if (mission.state or {}).get("results_stale"):
            raise ValidationError({"offer_id": "شرایط خرید تغییر کرده‌اند؛ ابتدا نتایج را تازه کن."})
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
                "visit_plan": visit_plan,
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
