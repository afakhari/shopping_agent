#!/usr/bin/env python
"""Django's command-line utility."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - environment setup error
        raise ImportError(
            "Django is not installed. Install dependencies with "
            "`python -m pip install -r requirements-dev.txt`."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
