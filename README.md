# University Smart Assistant

A Persian-first, RTL web platform where university students ask academic
questions — about courses, prerequisites, terms, schedules, exams, their own
enrolled courses and official regulations — and get answers grounded in the
university's structured database or in official lecture documents through
retrieval-augmented generation, with citations.

The assistant is not the source of truth for university facts: deterministic
backend rules and official data decide, and the LLM explains. See
[`university-assistant-docs/AGENTS.md`](university-assistant-docs/AGENTS.md)
for the project contract.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, TypeScript, Tailwind, React Router (Persian/RTL) |
| Backend | Django 5.2 LTS, Django REST Framework, Gunicorn |
| Database | PostgreSQL 16 + pgvector (the only supported engine) |
| Background jobs | Celery + Redis |
| AI | Provider-agnostic adapter; `mock` for offline demos, `groq` for a real LLM |
| Local serving | nginx static build + reverse proxy, Docker Compose |

API routes live under `/api/v1/`. The generated
[`openapi.yaml`](openapi.yaml) is the contract (ADR-012).

## Quick start (local production-like demo)

Prerequisites: Docker Desktop (or Docker Engine + Compose v2), 8 GB RAM
recommended, port `8080` free.

```powershell
scripts/init-env.ps1        # creates .env with random local secrets
scripts/deploy-local.ps1    # build → migrate → seed demo → start → wait ready
```

Open <http://localhost:8080>.

The full runbook — manual commands, environment variables, migrations, demo
accounts, backups, restore, rollback, health checks, troubleshooting and known
limitations — is in **[DEPLOYMENT.md](DEPLOYMENT.md)**.

### Manual start

```bash
cp .env.example .env
# Replace every __CHANGE_ME__ placeholder in .env.

docker compose up -d --build db redis
docker compose run --rm backend python manage.py migrate --noinput
docker compose run --rm backend python manage.py seed_demo
docker compose up -d --build
```

Migrations are a separate, controlled step by design; `docker compose up`
never migrates automatically.

## Demo accounts

All four accounts use `DEMO_PASSWORD` from your local `.env`:

| Role | Email |
|---|---|
| SUPERADMIN | `root@semnan.local` |
| ADMIN | `admin@semnan.local` |
| STUDENT | `student@semnan.local` |
| PROFESSOR | `professor@semnan.local` |

Print them locally (never commit the output):

```powershell
scripts/show-demo-credentials.ps1
```

## URLs

| Purpose | URL |
|---|---|
| App | <http://localhost:8080> |
| API health | <http://localhost:8080/api/v1/health/> |
| Liveness / readiness / deep health | `/health/live/`, `/health/ready/`, `/health/deep/` |
| Swagger UI | <http://localhost:8080/api/v1/schema/swagger-ui/> |

## Common commands

| Where | Command | Does |
|---|---|---|
| root | `scripts/test-backend.ps1` | Full backend suite against disposable PostgreSQL + pgvector |
| `backend/` | `python -m ruff check .` | Lint |
| `backend/` | `python manage.py makemigrations --check --dry-run` | Fails if a migration is missing |
| `frontend/` | `npm run test` | Unit tests (vitest) |
| `frontend/` | `npm run typecheck` | Type checking |
| `frontend/` | `npm run build` | Production bundle in `dist/` |
| root | `docker compose config --quiet` | Validate Compose |
| root | `scripts/smoke-test.ps1` | Post-deploy smoke tests |
| root | `scripts/backup.ps1` | Timestamped, validated PostgreSQL backup |
| root | `scripts/restore-drill.ps1` | Restore into a temporary DB and verify |
| root | `scripts/secret-scan.ps1` | Tracked files, Git history, ignore rules |
| root | `scripts/rollback-rehearsal.ps1` | Safe image rollback rehearsal |

## Development without the release stack

```bash
# API
cd backend
python -m venv .venv
.venv/Scripts/activate          # source .venv/bin/activate on Linux/macOS
pip install -r requirements-dev.txt
# Set DATABASE_URL to a PostgreSQL + pgvector server; SQLite is not supported.
python manage.py migrate
# Demo identities are created only when DEMO_PASSWORD is set; otherwise the
# dataset is seeded and demo accounts are skipped.
python manage.py seed
python manage.py runserver
```

```bash
# Frontend (Vite dev server, proxies /api to Django)
cd frontend
npm install
npm run dev
```

The Docker development overlay keeps the old bind-mount/runserver/Vite
workflow:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Layout

| Path | Purpose |
|---|---|
| `backend/` | Django + DRF API (`/api/v1/...`), Celery worker, Gunicorn config |
| `frontend/` | React + Vite SPA, nginx production image |
| `data/` | Read-only academic dataset used by `seed` / `seed_demo` |
| `scripts/` | Local release, test, backup, restore, smoke-test and scan helpers |
| `university-assistant-docs/` | Requirements, architecture, ADRs, phase records |
| `docker-compose.yml` | Local release stack (db, redis, backend, worker, web) |
| `DEPLOYMENT.md` | Complete local deployment and recovery runbook |

## Security and data

- Never commit `.env` or real secrets; `.env` is gitignored and `.env.example`
  contains placeholders only.
- The release entrypoint refuses insecure defaults (DEBUG, weak secrets,
  implicit cookie/HTTPS flags, missing provider choice).
- The browser never receives AI provider keys.
- PostgreSQL data, Redis data and uploaded documents live in named volumes and
  survive `docker compose down`. Only `down -v` deletes them.
- Backups are written to the gitignored `backups/` directory with timestamped
  names and a retention policy.

## Phase status

Phase 16 — Local Production-Ready Release & Demo Deployment — is the current
phase. Evidence and acceptance status are recorded in
[`university-assistant-docs/docs/phases/phase-16.md`](university-assistant-docs/docs/phases/phase-16.md).
No later phase has been started.

The full specification lives in
[`university-assistant-docs/START-HERE.md`](university-assistant-docs/START-HERE.md).
