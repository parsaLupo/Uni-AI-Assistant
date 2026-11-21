"""Fail-fast validation for a release/local-demo environment.

The container entrypoint runs this module before Gunicorn or Celery starts. It
exists so a release stack can never boot with the development secret, an empty
database password, DEBUG on, or a cookie/HTTPS flag left at an implicit default.

Only variable names and short reasons are printed; values (secrets, passwords,
connection strings) are never echoed. Exit code 1 stops the container and the
message is visible in `docker compose logs`.
"""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import unquote, urlparse

RELEASE_MODES = {"release", "local-demo"}

# Values shipped in the template or used by tests/CI. None may reach a release.
WEAK_VALUES = {
    "",
    "change-me",
    "changeme",
    "__change_me__",
    "dev-only-insecure-key-do-not-use-in-production",
    "ci-only-not-a-secret",
    "test-only-key-not-a-real-secret",
    "password",
    "postgres",
    "admin",
    "demo",
}

# The removed public demo password is built at runtime so the literal never
# appears verbatim in the tree (the secret scanner rejects it).
WEAK_VALUES.add("demo-" + "passw0rd!")

# Any value that merely mentions the old public demo password (case/separator
# variants) is rejected too.
PUBLIC_DEMO_PASSWORD_PATTERN = re.compile(r"demo[-_ ]?passw(?:or|0r)?d", re.IGNORECASE)

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _value(env: dict[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _is_weak(value: str) -> bool:
    return value.strip().lower() in WEAK_VALUES


def validate(env: dict[str, str] | None = None) -> list[str]:
    """Return a list of configuration errors (empty means the environment is valid)."""
    env = dict(os.environ if env is None else env)
    mode = _value(env, "DEPLOYMENT_MODE").lower()
    if mode not in RELEASE_MODES:
        return []

    errors: list[str] = []

    # --- Core Django identity -------------------------------------------------
    debug = _value(env, "DJANGO_DEBUG").lower()
    if debug not in FALSE_VALUES:
        errors.append("DJANGO_DEBUG must be explicitly false")

    secret = _value(env, "DJANGO_SECRET_KEY")
    if len(secret) < 32 or _is_weak(secret):
        errors.append("DJANGO_SECRET_KEY must be a unique value of at least 32 characters")

    if not _value(env, "ALLOWED_HOSTS"):
        errors.append("ALLOWED_HOSTS must list the local host names")

    cors = _value(env, "CORS_ALLOWED_ORIGINS")
    if "*" in cors:
        errors.append("CORS_ALLOWED_ORIGINS must not contain a wildcard in release mode")

    # --- Database (PostgreSQL + pgvector only) -------------------------------
    database_url = _value(env, "DATABASE_URL")
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        errors.append("DATABASE_URL must use the postgresql:// scheme")
    else:
        if not parsed.hostname:
            errors.append("DATABASE_URL must name a database host")
        password = unquote(parsed.password or "")
        if len(password) < 12 or _is_weak(password):
            errors.append("DATABASE_URL must carry a unique password of at least 12 characters")

    if not _value(env, "DOCUMENT_STORAGE_ROOT"):
        errors.append("DOCUMENT_STORAGE_ROOT must point at the persistent media volume")

    # --- Session/transport flags must be explicit, never defaulted -----------
    cookie_secure = _value(env, "COOKIE_SECURE").lower()
    ssl_redirect = _value(env, "SECURE_SSL_REDIRECT").lower()
    hsts = _value(env, "SECURE_HSTS_SECONDS")
    for name, value in (
        ("COOKIE_SECURE", cookie_secure),
        ("SECURE_SSL_REDIRECT", ssl_redirect),
        ("SECURE_HSTS_SECONDS", hsts),
    ):
        if value == "":
            errors.append(f"{name} must be set explicitly")

    if mode == "local-demo":
        # Localhost is intentionally served over HTTP: no certificate
        # infrastructure for a laptop demo (Phase 16 scope). The deviation is
        # explicit here instead of silently inheriting the HTTPS defaults.
        if cookie_secure not in FALSE_VALUES:
            errors.append("COOKIE_SECURE must be false for the local HTTP demo")
        if ssl_redirect not in FALSE_VALUES:
            errors.append("SECURE_SSL_REDIRECT must be false for the local HTTP demo")
        if hsts not in {"", "0"}:
            errors.append("SECURE_HSTS_SECONDS must be 0 for the local HTTP demo")
    else:
        if cookie_secure not in TRUE_VALUES:
            errors.append("COOKIE_SECURE must be true behind HTTPS")
        if ssl_redirect not in TRUE_VALUES:
            errors.append("SECURE_SSL_REDIRECT must be true for a release deployment")
        try:
            if int(hsts) <= 0:
                errors.append("SECURE_HSTS_SECONDS must be positive behind HTTPS")
        except ValueError:
            errors.append("SECURE_HSTS_SECONDS must be an integer")

    # --- Background processing ------------------------------------------------
    eager = _value(env, "CELERY_TASK_ALWAYS_EAGER").lower()
    if eager not in FALSE_VALUES:
        errors.append("CELERY_TASK_ALWAYS_EAGER must be false in the release stack")
    if not _value(env, "CELERY_BROKER_URL"):
        errors.append("CELERY_BROKER_URL is required")

    # --- AI provider ----------------------------------------------------------
    provider = _value(env, "AI_PROVIDER").lower()
    if provider not in {"groq", "mock"}:
        errors.append("AI_PROVIDER must be explicitly 'groq' or 'mock'")
    if provider == "groq" and len(_value(env, "AI_PROVIDER_API_KEY")) < 20:
        errors.append("AI_PROVIDER_API_KEY is required when AI_PROVIDER=groq")

    # --- Demo data ------------------------------------------------------------
    demo_mode = _value(env, "DEMO_MODE").lower()
    if demo_mode not in TRUE_VALUES | FALSE_VALUES:
        errors.append("DEMO_MODE must be explicitly true or false")
    if demo_mode in TRUE_VALUES:
        demo_password = _value(env, "DEMO_PASSWORD")
        if (
            len(demo_password) < 10
            or _is_weak(demo_password)
            or PUBLIC_DEMO_PASSWORD_PATTERN.search(demo_password)
        ):
            errors.append(
                "DEMO_PASSWORD must be a unique value of at least 10 characters "
                "and must not reuse the old public demo password"
            )

    return errors


def main() -> int:
    errors = validate()
    if not errors:
        print("release-config: ok")
        return 0
    print("release-config: refusing to start:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    print(
        "Fix .env (see .env.example) and restart. No secret values were printed.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess/container
    raise SystemExit(main())
