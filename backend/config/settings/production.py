"""Production settings with fail-fast secret and host validation."""
import os
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
if not SECRET_KEY or SECRET_KEY == "local-only-insecure-key-change-before-deploy":  # noqa: F405
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
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Defence in depth for an anonymous public API. An edge/global quota is still
# essential: Django's default per-process cache is not a distributed rate limiter.
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = [
    "rest_framework.throttling.AnonRateThrottle",
]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": os.environ.get("DJANGO_ANON_RATE", "120/min"),
}

# A listening web process is not production-ready until the catalog is populated.
REQUIRE_DATASET_FOR_READINESS = True
