"""Shared Django settings. Environment-specific policy lives in local.py/production.py."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.health.apps.HealthConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.search.apps.SearchConfig",
    "apps.missions.apps.MissionsConfig",
    "apps.agent.apps.AgentConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def _database_config() -> dict[str, object]:
    """Support PostgreSQL URLs in Docker and SQLite for dependency-light local checks."""
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}

    parsed = urlparse(raw_url)
    if parsed.scheme in {"postgres", "postgresql", "postgresql+psycopg"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or 5432,
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))},
        }
    if parsed.scheme == "sqlite":
        name = unquote(parsed.path)
        if name in {"", "/:memory:"}:
            name = ":memory:"
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name}
    raise ValueError("DATABASE_URL must use postgresql://, postgres://, or sqlite://.")


DATABASES = {"default": _database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "config.api_errors.custom_exception_handler",
}

DATASET_RAW_DIR = Path(os.environ.get("DATASET_RAW_DIR", str(BASE_DIR.parent / "data" / "raw")))
DATASET_IMPORT_BATCH_SIZE = int(os.environ.get("DATASET_IMPORT_BATCH_SIZE", "2000"))
DATASET_REPORT_DIR = Path(os.environ.get("DATASET_REPORT_DIR", str(BASE_DIR.parent / "reports")))
MAX_REASONABLE_PRICE_TOMAN = int(os.environ.get("MAX_REASONABLE_PRICE_TOMAN", "100000000000"))
DEMO_CONTACT_OUTCOMES = os.environ.get(
    "DEMO_CONTACT_OUTCOMES", "no_answer,confirmed_available,unavailable,closed,error,price_changed"
)
LLM_ENABLED = os.environ.get("LLM_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai_compatible").strip()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
LLM_MODEL = os.environ.get("LLM_MODEL", "").strip()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").strip()
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "6"))

# Neshan is an OPTIONAL, billable service; disabled until a separately scoped
# REST key, a verified quota and a safe operational budget are configured.
NESHAN_ROUTING_ENABLED = os.environ.get("NESHAN_ROUTING_ENABLED", "0") == "1"
NESHAN_ROUTING_API_KEY = os.environ.get("NESHAN_ROUTING_API_KEY", "").strip()
NESHAN_ROUTING_MAX_CALLS_PER_MISSION = max(
    0, min(10, int(os.environ.get("NESHAN_ROUTING_MAX_CALLS_PER_MISSION", "0")))
)
NESHAN_ROUTING_DAILY_MAX_CALLS = max(
    0, min(100, int(os.environ.get("NESHAN_ROUTING_DAILY_MAX_CALLS", "0")))
)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
