# Phase 01 — Architecture and API Contract

## Status

`DONE` — 2026-10-05. Design phase, closed with a contract review. See the
verification record at the end of this file.

## Objective
Design the technical boundaries before feature implementation.

## Tasks
- [x] Define Django app boundaries. — `docs/02` §4.1 (entity → app → URL prefix).
- [x] Define React feature boundaries. — `docs/02` §4.2.
- [x] Define database entities. — `docs/03` ERD, plus §6 constraints (previously missing).
- [x] Define REST naming and error contract. — `docs/04`, `docs/api/admin.md`, and the generated `openapi.yaml` (ADR-012).
- [x] Define authentication strategy. — `docs/05` + ADR-004 (unchanged; CSRF/rotation recorded as Phase 03 decisions).
- [x] Define AI/RAG boundary. — `docs/06` §10 (unchanged; provider adapter ADR-006).
- [x] Record important decisions as ADRs. — ADR-011 background worker, ADR-012 OpenAPI contract, ADR-013 frontend data layer.

## Deliverables
- architecture document — `docs/02` (reviewed against `architecture.md`)
- ERD — `docs/03`
- API catalog — `docs/04` + `docs/api/admin.md` + `openapi.yaml`
- auth design — `docs/05`
- RAG architecture — `docs/06`
- ADRs — `docs/decisions/`

## Acceptance criteria
- [x] Major components and data flows are documented. — `docs/02` §1–§7, `docs/06` §2/§4.
- [x] Core entities are identified. — `docs/03`; each entity now has exactly one owning app (`docs/02` §4.1) and its database constraints (`docs/03` §6).
- [x] API versioning is defined. — `/api/v1/` prefix, committed `openapi.yaml`, CI drift gate (ADR-012).
- [x] Security boundaries are explicit. — `docs/07`, `docs/02` §7, and a permission level per admin endpoint in `docs/api/admin.md`.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Verification record (2026-10-05)

Design phase — no feature code, so the gate is contract validation rather than runtime tests. Verified:

| Check | Command | Result |
|---|---|---|
| OpenAPI generates + validates | `python manage.py spectacular --file ../openapi.yaml --validate` | exit 0, 0 errors, 0 warnings |
| Contract is complete | `openapi.yaml` | lists only `/api/v1/health/`; schema/swagger/catch-all excluded by design |
| Contract tests | `python -m pytest apps/common/tests/test_openapi.py` | 3 passed |
| Full suite | `python -m pytest` | 18 passed (SQLite) and 18 passed against PostgreSQL |
| Lint | `python -m ruff check .` | clean |
| Migrations | `python manage.py makemigrations --check --dry-run` | no changes |
| Admin catalog documented | `docs/api/admin.md` | 30+ endpoints, permission level per endpoint |
| Constraints documented | `docs/03` §6 | 7 constraints, each justified |
| ADRs | ADR-011, ADR-012, ADR-013 | recorded |

Migrations: none (design phase). Installed dependency: `drf-spectacular==0.30.0`, documented in `backend/requirements.txt` and ADR-012 per AGENTS rule 10.

## Review note — does any Phase 03–16 task need an undocumented contract?

No. Every endpoint those phases implement is catalogued (`docs/04`, `docs/api/*.md`, `docs/api/admin.md`) and lands in `openapi.yaml` when implemented:

- Phase 03 auth — `docs/05` + `docs/api/auth.md`; four decisions remain open (OA-01 registration policy, OA-02 identifier, OA-09 rate limits, CSRF strategy). These are behaviour/config decisions, not missing contracts.
- Phase 04 models + write APIs — `docs/03` (entities + constraints) + `docs/api/admin.md`.
- Phases 06/10 UI routes — `docs/20` + `docs/02` §4.2.
- Phases 07–09 — `docs/06`, `docs/07`, and existing `docs/api/documents.md` / `docs/api/chat.md`.
- Phases 11–13 (post-MVP) — `docs/api/courses.md`, `docs/04` §6 analytics.

Carried into later phases by decision, not gap: the Jalali date library (OA-18) and the frontend data-layer package (ADR-013) are choices recorded now and implemented in Phases 04/05.
