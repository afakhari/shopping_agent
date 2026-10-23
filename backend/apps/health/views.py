"""Small health endpoints with non-secret LLM configuration diagnostics."""
import logging

from django.conf import settings
from django.db import connections

from apps.catalog.models import Offer, Product, Shop
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.agent.llm import configuration_diagnostics

logger = logging.getLogger(__name__)


@require_GET
def live(_request):
    """Liveness only: confirms the web process can serve a request."""
    return JsonResponse({"status": "alive"})


@require_GET
def ready(_request):
    """Readiness: confirms the database and reports safe model-configuration flags."""
    try:
        connections["default"].ensure_connection()
    except (DatabaseError, OSError) as exc:
        logger.warning("Readiness check failed: database unavailable (%s)", type(exc).__name__)
        return JsonResponse(
            {"status": "not_ready", "checks": {"database": "error"}}, status=503
        )

    # Production readiness must not go green with an empty or partially imported catalog.
    # Keep lightweight development environments usable without the challenge dataset.
    checks = {"database": "ok"}
    if getattr(settings, "REQUIRE_DATASET_FOR_READINESS", False):
        try:
            populated = {
                "products": Product.objects.exists(),
                "shops": Shop.objects.exists(),
                "offers": Offer.objects.exists(),
            }
        except DatabaseError:
            return JsonResponse(
                {"status": "not_ready", "checks": {"database": "ok", "catalog": "error"}},
                status=503,
            )
        checks["catalog"] = "ok" if all(populated.values()) else "incomplete"
        minimums = getattr(settings, "CATALOG_MINIMUM_ROWS", None)
        if checks["catalog"] == "ok" and isinstance(minimums, dict) and minimums:
            try:
                counts = {
                    "products": Product.objects.count(), "shops": Shop.objects.count(),
                    "offers": Offer.objects.count(),
                }
            except DatabaseError:
                return JsonResponse(
                    {"status": "not_ready", "checks": {"database": "ok", "catalog": "error"}},
                    status=503,
                )
            if any(counts.get(key, 0) < minimum for key, minimum in minimums.items()):
                checks["catalog"] = "incomplete"
        if checks["catalog"] != "ok":
            return JsonResponse({"status": "not_ready", "checks": checks}, status=503)

    llm = configuration_diagnostics()
    return JsonResponse({
        "status": "ready",
        "checks": checks,
        "agent_mode": "model_configured" if llm["status"] == "configured" else "deterministic_fallback",
        # Safe boolean/status data only. Never disclose secrets, model names, or provider URLs.
        "llm": llm,
    })
