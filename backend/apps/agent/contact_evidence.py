"""Evidence fields for simulated pre-visit questions.

An offer is historical catalog data. The demo simulator can model a seller's
availability outcome but does not make external price/hour calls. Keep the two
sources distinct in the API, saved snapshots and any user-facing UI.
"""
from __future__ import annotations

from apps.catalog.models import Offer
from apps.catalog.services.visit_context import opening_status
from apps.missions.visit_plan import format_weekly_hours


def build_contact_evidence(
    offer: Offer, outcome: str, questions: list[str]
) -> dict[str, dict[str, object]]:
    evidence: dict[str, dict[str, object]] = {}
    if "stock" in questions:
        evidence["stock"] = {
            "status": outcome,
            "source": "demo_simulation",
            "verified_in_real_world": False,
        }
    if "price" in questions:
        evidence["price"] = {
            "status": "simulated_change_amount_unknown" if outcome == "price_changed"
            else "registered_not_live_verified",
            "registered_price_toman": str(offer.price_toman)
            if offer.price_toman is not None else None,
            "last_price_changed_at": offer.last_price_changed_at.isoformat()
            if offer.last_price_changed_at else None,
            "source": "dataset_snapshot",
            "verified_in_real_world": False,
        }
    if "hours" in questions:
        evidence["hours"] = {
            "status": "registered_not_live_verified",
            "weekly_hours": format_weekly_hours(offer.shop.weekly_hours),
            "opening_status": opening_status(offer.shop.weekly_hours),
            "source": "dataset_snapshot",
            "verified_in_real_world": False,
        }
    return evidence
