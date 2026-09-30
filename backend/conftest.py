"""Test bootstrap.

Fixes a deterministic environment before Django settings are imported, so the
suite behaves identically on a developer machine and in CI:

* ``DATABASE_URL`` is forced empty so the suite uses SQLite even if a local
  ``backend/.env`` points at a Docker PostgreSQL that is not running.
* ``DJANGO_SECRET_KEY`` is a throwaway value; no secret is ever committed.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key-not-a-real-secret")
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost")
os.environ.setdefault("DJANGO_DEBUG", "false")
