#!/usr/bin/env python
"""Django management entry point for the University Smart Assistant backend."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - developer environment issue
        raise ImportError(
            "Couldn't import Django. Activate the backend virtual environment "
            "(backend/.venv) or run the stack through Docker Compose."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
