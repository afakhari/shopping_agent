"""Application services for mission state, event sequencing, and contact simulation."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.missions.models import MissionEvent, PurchaseMission


def public_event(mission_id: str, seq: int, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mission_id": str(mission_id),
        "seq": seq,
        "type": event_type,
        "payload": payload,
    }


def append_events_locked(
    mission: PurchaseMission, events: list[tuple[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Persist ordered events. Caller should hold a transaction/row lock for this mission."""
    rows: list[MissionEvent] = []
    envelopes: list[dict[str, Any]] = []
    seq = mission.last_event_seq
    now = timezone.now()
    for event_type, payload in events:
        seq += 1
        rows.append(
            MissionEvent(
                mission=mission,
                seq=seq,
                event_type=event_type,
                payload=payload,
                created_at=now,
            )
        )
        envelopes.append(public_event(str(mission.pk), seq, event_type, payload))
    if rows:
        MissionEvent.objects.bulk_create(rows)
        mission.last_event_seq = seq
        mission.save(update_fields=["last_event_seq", "updated_at"])
    return envelopes


def serialize_mission(mission: PurchaseMission, *, include_events: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mission_id": str(mission.pk),
        "status": mission.status,
        "current_stage": mission.current_stage,
        "initial_message": mission.initial_message,
        "constraints": mission.constraints,
        "state": mission.state,
        "last_event_seq": mission.last_event_seq,
        "created_at": mission.created_at.isoformat(),
        "updated_at": mission.updated_at.isoformat(),
    }
    if include_events:
        # Return the newest bounded window, but preserve chronological order for UI replay.
        recent_events = list(mission.events.order_by("-seq")[:100])
        recent_events.reverse()
        payload["events"] = [
            public_event(str(mission.pk), event.seq, event.event_type, event.payload)
            for event in recent_events
        ]
    return payload


def merged_constraints(existing: dict[str, Any], updates: dict[str, Any] | None) -> dict[str, Any]:
    result = {"city": "tehran", "sort": "relevance", **(existing or {})}
    result.update(updates or {})
    result["city"] = result.get("city", "tehran")
    result["sort"] = result.get("sort", "relevance")
    return result
