"""Configuration loaded from environment variables.

`docs/09-deployment.md` section 3 requires environment-based configuration and
states that variable names must match `.env.example`. `.env` files are read only
as a local convenience (Docker Compose injects variables directly), and an
explicit process variable always wins over a `.env` entry.

A third-party dotenv package is deliberately not used; see ADR-008.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path: Path | None = None) -> None:
    """Load simple ``KEY=VALUE`` lines from ``backend/.env`` when present."""
    env_path = path or BASE_DIR / ".env"
    if not env_path.is_file():
        return
    # Under pytest the database decision belongs to the test harness
    # (backend/conftest.py), not to a local .env: pytest-django imports these
    # settings *before* the root conftest runs, so a .env DATABASE_URL would be
    # frozen into DATABASES and point the suite at a (possibly down) server.
    _under_pytest = "pytest" in sys.modules
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        if _under_pytest and key == "DATABASE_URL" and key not in os.environ:
            # Absent: the promotion block below decides (SQLite or TEST_DATABASE_URL).
            continue
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


load_env_file()

if "pytest" in sys.modules and not os.environ.get("DATABASE_URL"):
    # Order-independent twin of conftest.py: if settings were imported before
    # the conftest could promote TEST_DATABASE_URL, do it here so CI's
    # PostgreSQL runs keep exercising the real engine (pipeline.md P-06).
    _test_url = os.environ.pop("TEST_DATABASE_URL", None)
    os.environ["DATABASE_URL"] = _test_url or ""

SUPPORTED_DB_SCHEMES = {"postgres", "postgresql"}


def env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_list(name: str, default: tuple[str, ...] = ()) -> list[str]:
    value = os.environ.get(name)
    if value is None or value == "":
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def database_config() -> dict:
    """Build Django DATABASES entry from ``DATABASE_URL``.

    PostgreSQL + pgvector is the only supported database engine (ADR-002).
    ``DATABASE_URL`` must always be set; there is no SQLite fallback.
    """
    url = env_str("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL is required. PostgreSQL + pgvector is the only "
            "supported database engine; SQLite fallback has been removed."
        )

    parsed = urlparse(url)
    if parsed.scheme not in SUPPORTED_DB_SCHEMES:
        raise ValueError(
            f"Unsupported DATABASE_URL scheme '{parsed.scheme}'. "
            f"Expected one of: {', '.join(sorted(SUPPORTED_DB_SCHEMES))}."
        )

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
        # Fail fast instead of hanging for minutes when PostgreSQL is unreachable.
        "OPTIONS": {"connect_timeout": 10},
    }
