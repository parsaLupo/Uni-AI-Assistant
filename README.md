# University AI Assistant

A web platform where university students ask academic questions — about courses,
prerequisites, terms, schedules and their own enrolled courses — and get answers
either from the university's structured database or from lecture documents through
retrieval augmented generation, with citations.

Phase status and the full specification live in
[`university-assistant-docs/`](university-assistant-docs/START-HERE.md). Start any
work by reading `university-assistant-docs/AGENTS.md`, then
`university-assistant-docs/START-HERE.md`. Current phase: **PHASE_00** (`DONE`,
re-validated after the Persian/RTL documentation amendment); next up **PHASE_01**.

The product is Persian-first: the UI is Persian and RTL, user-facing API messages
are Persian, and the assistant will answer in Persian by default. Technical
identifiers — code, API field names, error codes, database columns — stay English
(ADR-010).

## Layout

| Path | Purpose |
|---|---|
| `backend/` | Django 5.2 LTS + Django REST Framework API (`/api/v1/...`) |
| `frontend/` | React 19 + Vite + TypeScript single page app |
| `university-assistant-docs/` | Requirements, design, phases, ADRs — the contract this code implements |
| `docker-compose.yml` | PostgreSQL + pgvector, API, web dev server |
| `.github/workflows/ci.yml` | Lint, typecheck, tests, build on every push and pull request |

`backend/apps/` holds one Django app per bounded context (`accounts`, `academic`,
`documents`, `assistant`, and so on); `apps/common/` holds the shared request id
middleware, structured logging, health endpoint and the error envelope that
`frontend/src/api/client.ts` mirrors.

## Local development

Docker path (requires a running Docker daemon):

```bash
cp .env.example .env
docker compose up --build
```

Then the API is on <http://localhost:8000/api/v1/health/> and the app on
<http://localhost:5173>.

Without Docker, run the two tiers directly. The API falls back to a SQLite file
when `DATABASE_URL` is empty, which is enough for Phase 00 and 01 work but not for
vector features:

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows; source .venv/bin/activate on Linux/macOS
pip install -r requirements-dev.txt
cp ../.env.example .env
python manage.py migrate
python manage.py runserver
```

```bash
cd frontend
npm install
npm run dev
```

## Commands

| Where | Command | Does |
|---|---|---|
| `backend/` | `python -m pytest` | API tests (SQLite, no Docker needed) |
| `backend/` | `python -m ruff check .` | Lint |
| `backend/` | `python manage.py makemigrations --check --dry-run` | Fails if a migration is missing |
| `frontend/` | `npm run test` | Unit tests (vitest) |
| `frontend/` | `npm run typecheck` | Type checking |
| `frontend/` | `npm run build` | Production bundle in `dist/` |

Never commit `.env` or real secrets; `docs/07-security.md` and `AGENTS.md` govern
configuration and `docs/19-git-and-release.md` govern branches, commits and tags.
