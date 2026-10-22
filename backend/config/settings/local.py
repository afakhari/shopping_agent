"""Local and test settings. Never use these settings for public production."""
import os

from . import base as base_settings
from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "1").lower() in {"1", "true", "yes"}
SECRET_KEY = base_settings.SECRET_KEY or "local-only-insecure-key-change-before-deploy"
ALLOWED_HOSTS = list(
    dict.fromkeys([*base_settings.ALLOWED_HOSTS, "testserver", "backend", "0.0.0.0"])
)
