"""Small health endpoints with non-secret LLM configuration diagnostics."""
import logging

from django.db import connections
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

    llm = configuration_diagnostics()
    return JsonResponse({
        "status": "ready",
        "checks": {"database": "ok"},
        "agent_mode": "model_configured" if llm["status"] == "configured" else "deterministic_fallback",
        # Safe boolean/status data only. Never disclose secrets, model names, or provider URLs.
        "llm": llm,
    })
