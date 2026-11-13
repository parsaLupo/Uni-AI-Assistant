"""Production settings boot checks (docs/07-security.md section 1, Phase 15).

These checks run the real settings module in a clean subprocess with
`DJANGO_DEBUG=false`, because the pytest process itself imports settings once
with the test-friendly defaults (`IS_TESTS` keeps the HTTPS redirect off
there) and `override_settings` cannot re-run the boot-time guards.

Covered here:
- security flags default ON outside development (HTTPS redirect, HSTS,
  no-sniff, referrer policy, clickjacking),
- secure cookies, empty CORS when nothing is configured,
- an explicit `DJANGO_SECRET_KEY` is required to boot.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

BOOT_SCRIPT = """
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import json, sys
import django
django.setup()
from django.conf import settings as s
from django.core.exceptions import ImproperlyConfigured
print(json.dumps({
    "DEBUG": s.DEBUG,
    "SECURE_SSL_REDIRECT": s.SECURE_SSL_REDIRECT,
    "SECURE_HSTS_SECONDS": s.SECURE_HSTS_SECONDS,
    "SECURE_CONTENT_TYPE_NOSNIFF": s.SECURE_CONTENT_TYPE_NOSNIFF,
    "SECURE_REFERRER_POLICY": s.SECURE_REFERRER_POLICY,
    "X_FRAME_OPTIONS": s.X_FRAME_OPTIONS,
    "SECURE_PROXY_SSL_HEADER": list(s.SECURE_PROXY_SSL_HEADER),
    "COOKIE_SECURE": s.COOKIE_SECURE,
    "SESSION_COOKIE_SECURE": s.SESSION_COOKIE_SECURE,
    "CORS_ALLOWED_ORIGINS": s.CORS_ALLOWED_ORIGINS,
    "ALLOWED_HOSTS": s.ALLOWED_HOSTS,
}))
"""


def _prod_env(**extra):
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "DJANGO_DEBUG",
            "DJANGO_SECRET_KEY",
            "ALLOWED_HOSTS",
            "CORS_ALLOWED_ORIGINS",
            "SECURE_SSL_REDIRECT",
            "SECURE_HSTS_SECONDS",
            "COOKIE_SECURE",
        }
    }
    env.update(
        {
            "DJANGO_DEBUG": "false",
            "DJANGO_SECRET_KEY": "prod-test-secret-not-used-anywhere",
            "ALLOWED_HOSTS": "assistant.semnan.ac.ir,backend",
            "DATABASE_URL": "postgresql://usa_user:unused@localhost:5432/usa_prod",
            # Explicit empties beat the developer .env that load_env_file()
            # picks up in a working checkout (setdefault only fills gaps).
            "CORS_ALLOWED_ORIGINS": "",
        }
    )
    env.update(extra)
    return env


def _run(env, script=BOOT_SCRIPT):
    # backend/apps/common/tests/ -> backend/
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_production_defaults_enable_transport_hardening():
    result = _run(_prod_env())

    assert result.returncode == 0, result.stderr
    flags = json.loads(result.stdout.strip().splitlines()[-1])
    assert flags["DEBUG"] is False
    assert flags["SECURE_SSL_REDIRECT"] is True
    assert flags["SECURE_HSTS_SECONDS"] == 31536000
    assert flags["SECURE_CONTENT_TYPE_NOSNIFF"] is True
    assert flags["SECURE_REFERRER_POLICY"] == "same-origin"
    assert flags["X_FRAME_OPTIONS"] == "DENY"
    assert flags["SECURE_PROXY_SSL_HEADER"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert flags["COOKIE_SECURE"] is True
    assert flags["SESSION_COOKIE_SECURE"] is True


def test_production_cors_stays_empty_without_explicit_origins():
    result = _run(_prod_env())

    assert result.returncode == 0, result.stderr
    flags = json.loads(result.stdout.strip().splitlines()[-1])
    assert flags["CORS_ALLOWED_ORIGINS"] == []
    assert flags["ALLOWED_HOSTS"] == ["assistant.semnan.ac.ir", "backend"]


def test_production_boot_refuses_to_start_without_a_secret():
    # Empty string is an explicit "not configured"; it also wins over the
    # developer .env file that would otherwise provide a dev secret.
    env = _prod_env(DJANGO_SECRET_KEY="")

    result = _run(env, script="import django; django.setup()")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY is required" in result.stderr
