"""Test bootstrap.

Fixes a deterministic environment before Django settings are imported:

* By default ``DATABASE_URL`` is forced empty so the suite uses SQLite even if a
  local ``backend/.env`` points at a Docker PostgreSQL that is not running.
* Setting ``TEST_DATABASE_URL`` opts that run into a real PostgreSQL database.
  CI and the Phase 02 verification use it so pgvector/PostgreSQL behaviour is
  actually exercised (pipeline.md section 6, improvement I-01); a plain local
  ``pytest`` stays dependency-free.
* ``DJANGO_SECRET_KEY`` is a throwaway value; no secret is ever committed.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

_postgres_url = os.environ.pop("TEST_DATABASE_URL", None)
if _postgres_url:
    os.environ["DATABASE_URL"] = _postgres_url
else:
    os.environ["DATABASE_URL"] = ""

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key-not-a-real-secret")
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost")
os.environ.setdefault("DJANGO_DEBUG", "false")
