# Phase 02 — Project and Development Environment

## Status

`DONE` — 2026-10-05. Infrastructure tasks were delivered by the Phase 00 baseline;
this pass *verified* them against a running stack (improvement I-01) and fixed the
two configuration defects that verification exposed. See the verification record.

## Objective
Create a reproducible local development environment.

## Tasks
- [x] Initialize Django backend. — delivered by Phase 00 (Django 5.2 LTS + DRF).
- [x] Initialize React + TypeScript frontend. — delivered by Phase 00 (React 19 + Vite + TS).
- [x] Configure PostgreSQL. — compose `db` service, `pgvector/pgvector:0.8.6-pg16`; **verified connected** in this pass.
- [x] Enable pgvector capability. — migration `apps/common/migrations/0001_enable_pgvector.py`; **verified 0.8.6 + vector round-trip** in this pass.
- [x] Add environment configuration. — `backend/config/environment.py`, `.env.example`; boot guard refuses missing secrets.
- [x] Add Docker/Compose baseline. — `docker-compose.yml`; **machine-validated** (`docker compose config`) and **first successful `up --build`** in this pass.
- [x] Add health endpoint. — `GET /api/v1/health/`.
- [x] Add Git ignore and formatting/linting baseline. — `.gitignore`, ruff, CI.

## Acceptance criteria
- [x] Backend runs. — container up; `manage.py check` clean; suite 18 passed.
- [x] Frontend runs. — Vite dev container serves the Persian RTL shell; production build green.
- [x] PostgreSQL connects. — `GET /api/v1/health/` → `"database": "ok"` (latency 8–23 ms).
- [x] pgvector is available. — extension 0.8.6 present; `[1,2,3]::vector(3) <-> [3,2,1]::vector(3)` returned the correct distance.
- [x] Health endpoint responds. — 200 direct and through the frontend proxy.
- [x] Secrets are not committed. — `.env` ignored; `DEBUG=false` without `DJANGO_SECRET_KEY` refuses to boot.

## Non-goals
- no business features
- no AI integration

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Verification record (2026-10-05)

First time this stack was ever executed. Environment: Windows 11, Docker 28.3.2.

| Check | Command | Result |
|---|---|---|
| Compose file valid | `docker compose config --quiet` | valid (first machine validation) |
| Stack starts | `docker compose up -d --build` | db healthy, backend + frontend up |
| API ↔ PostgreSQL | `curl localhost:8000/api/v1/health/` | `200`, `checks.database = "ok"` |
| pgvector installed | `SELECT extversion FROM pg_extension` | `vector 0.8.6` (created by migration) |
| Vector round-trip | `[1,2,3]::vector(3) <-> [3,2,1]::vector(3)` | `2.8284` (√8 — correct) |
| Tests on SQLite | `python -m pytest` | 18 passed |
| Tests on PostgreSQL | `TEST_DATABASE_URL=… python -m pytest` | 18 passed (test DB created, extension applied) |
| Migrations | `python manage.py makemigrations --check --dry-run` | no changes |
| Frontend dev server | `curl localhost:5173/` | Persian RTL shell served |
| Full proxy chain | `curl localhost:5173/api/v1/health/` | `200` (browser → Vite → Django → PostgreSQL) |
| CI parity | `.github/workflows/ci.yml` | PostgreSQL+pgvector service, compose validation, OpenAPI drift gate |

Migrations: `apps/common/migrations/0001_enable_pgvector.py` (new; vendor-guarded
so SQLite test runs skip it).

## Defects found and fixed during verification

1. **Vite proxy hardcoded `http://localhost:8000`** — inside the frontend container
   `localhost` is the container itself, so the compose dev proxy could never reach
   Django. Fixed by reading `VITE_DEV_PROXY_TARGET` (already set in compose to
   `http://backend:8000`) with a localhost fallback.
2. **`ALLOWED_HOSTS` mismatch** — `.env.example` listed only
   `localhost,127.0.0.1`, which overrides compose's default (which includes
   `backend`), so proxied requests were rejected with `400 DisallowedHost`. Fixed
   in `.env.example` with a comment to keep it in sync with compose.

Both were invisible to unit tests and would have hit the next developer
immediately — the argument for running the stack, not just testing it.

3. **A new dependency does not reach a running container.** After Phase 01 added
   `drf-spectacular` to `requirements.txt`, the backend container kept crash-looping
   with `ModuleNotFoundError` (502 through the proxy) because the `./backend:/app`
   bind mount syncs *code*, not installed packages — and `docker compose up -d --build`
   built the new image without recreating the running container.
   Fix: `docker compose up -d --force-recreate backend` (the rebuilt image was
   already correct; only the container was stale).
   Rule for later phases: after changing dependencies, rebuild **and** force-recreate.
   Code-only edits need neither — autoreload handles them.
