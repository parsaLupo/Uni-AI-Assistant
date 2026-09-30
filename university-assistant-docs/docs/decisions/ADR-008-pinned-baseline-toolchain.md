# ADR-008 — Pinned baseline toolchain

## Status

Accepted

## Decision

Freeze the Phase 00 toolchain at the versions recorded in
`backend/requirements.txt`, `backend/requirements-dev.txt` and
`frontend/package.json`: Python 3.13, Django 5.2 LTS, Django REST Framework,
`psycopg[binary]`, pytest + pytest-django + ruff on the backend; React 19, Vite,
TypeScript, vitest on the frontend. Database is PostgreSQL with pgvector in
`docker-compose.yml`, while automated tests run against SQLite through
`backend/conftest.py`.

## Reasoning

`docs/09-deployment.md` section 5 warns against silent version drift across a
16-phase project, and ADR-001 froze the framework family but not the release
line. Django 5.2 is the current long term support line, so it survives the whole
MVP without a forced major upgrade mid-phase; the newer non LTS line would risk
breaking the eighteen later phases. SQLite for tests keeps the CI gate fast and
free of external services, as required by `docs/08-testing-strategy.md`.

## Consequences

Django is a release behind the newest feature line, so features introduced
after 5.2 cannot be used — this already surfaced once: `ObjectNotFoundError`
does not exist in 5.2 and is not imported (see ADR-009). Because SQLite cannot
exercise pgvector SQL, OA-06 records that a PostgreSQL service must be added to
CI in the phase that first ships vector queries. Upgrades are deliberate acts:
change the lock file, run the suite, record it here.
