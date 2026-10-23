"""Production settings with fail-fast secret and host validation."""
import os
from django.core.exceptions import ImproperlyConfigured

from . import base as base_settings
from .base import *  # noqa: F403

DEBUG = False
if not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY == "local-only-insecure-key-change-before-deploy":  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a strong, unique secret.")
production_hosts = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
if not production_hosts:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list the public backend host(s).")
ALLOWED_HOSTS = production_hosts

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
# Only trust a TLS proxy after loopback-binding the internal HTTP application.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
# Container health probes use internal HTTP, not the public reverse proxy.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/(live|ready)/$"]
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Defence in depth for an anonymous public API. An edge/global quota is still
# essential: Django's default per-process cache is not a distributed rate limiter.
REST_FRAMEWORK = {
    **base_settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DJANGO_ANON_RATE", "120/min"),
    },
}

# A listening web process is not production-ready until the catalog is populated.
REQUIRE_DATASET_FOR_READINESS = True
# Fixed competition snapshot counts; incomplete imports must not pass health probes.
CATALOG_MINIMUM_ROWS = {"products": 225903, "shops": 6476, "offers": 331506}
# Default zero disables paid model calls until the owner explicitly approves a budget.
LLM_DAILY_MAX_CALLS = max(0, min(10000, int(os.environ.get("LLM_DAILY_MAX_CALLS", "0"))))
