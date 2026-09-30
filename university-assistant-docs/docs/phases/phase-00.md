# Phase 00 — Discovery and Baseline

## Status

`DONE` — closed 2026-09-30. See the verification record at the end of this file.

## Objective
Freeze the first implementation baseline before writing production code.

## Tasks
- [x] Review project goals and use cases.
- [x] Confirm MVP boundaries.
- [x] Confirm actors and roles.
- [x] Confirm stack.
- [x] Identify open assumptions.
- [x] Define initial acceptance criteria.
- [x] Create repository structure.

## Deliverables
- approved `AGENTS.md`
- approved project overview
- requirements baseline
- phase plan
- initial README

## Acceptance criteria
- [x] MVP is clearly bounded. — `docs/13-project-scope.md` in/out of scope lists, confirmed against `docs/01-requirements.md`.
- [x] No critical requirement is ambiguous. — every remaining ambiguity is enumerated in `docs/21-open-assumptions.md` with the phase it blocks; none blocks Phase 01.
- [x] Repository and documentation structure exists. — `backend/` + `frontend/` + `docker-compose.yml` + `.github/workflows/ci.yml`, plus the versioned `university-assistant-docs/` tree; recorded in ADR-007.
- [x] Technology stack is frozen for MVP. — ADR-001 plus pinned versions and rationale in ADR-008.

## Non-goals
- no feature implementation
- no RAG implementation
- no UI implementation

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Verification record (closeout, 2026-09-30)

Environment: Windows, Python 3.13.5, Node 22, `backend/.venv`.

| Check | Command | Result |
|---|---|---|
| Backend tests | `python -m pytest` | 12 passed (health, error envelope, request id, settings contract) |
| Backend lint | `python -m ruff check .` | no findings |
| Config validity (debug off) | `python manage.py check` | system check identified no issues |
| Migration state | `python manage.py makemigrations --check --dry-run` | no changes detected |
| Frontend types | `npm run typecheck` | clean |
| Frontend tests | `npm run test` | 5 passed |
| Frontend build | `npm run build` | built, 220 kB / 68.9 kB gzip |
| Live response shape | `GET /api/v1/health/` | `200` with `status/service/version/request_id/checks`, `X-Request-ID` echoed |
| Unknown API path | `GET /api/v1/does-not-exist/` | `404` with `{"error":{"code":"NOT_FOUND","message","details"}}` |
| Access logging | same probe | `request_id=... method=GET path=... status=... latency_ms=...` |

Migrations created: none — Phase 00 ships no models by design (non-goal: no
feature implementation), so there is nothing to migrate.

### Known limitations

1. `docker compose up` was **not** executed: no Docker daemon is available in the
   authoring environment. The compose file is written against the pgvector image
   pinned in ADR-002 but is unverified; ADR-002 verification must happen in an
   environment with Docker before Phase 01 depends on it.
2. Tests run on SQLite; pgvector SQL is therefore untested (OA-06).
3. No authentication exists yet, so DRF's default `IsAuthenticated` makes every
   non-health endpoint return `401` until Phase 02 — intentional, and asserted by
   the settings contract test.
4. `OA-01` (registration policy) and `OA-02` (login identifier) must be answered
   before Phase 02 starts; they do not block Phase 01.

