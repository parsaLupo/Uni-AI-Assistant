# Phase 04 — Core Academic Data

## Objective
Build the normalized university data foundation.

## Models
- Faculty
- Department
- Course
- CoursePrerequisite
- Professor
- AcademicTerm
- CourseOffering
- ClassSchedule
- Exam
- StudentProfile
- Enrollment

## Tasks
- Implement models.
- Add migrations.
- Add admin/data management.
- Add serializers.
- Add CRUD/read APIs.
- Add permissions.
- Add filtering/search needed by MVP.

## Acceptance criteria
- [x] Models reflect ERD. — all 20 ERD entities implemented across 8 apps; `Announcement` + `Notification`/`AuditLog` included (V-13); constraints & indexes per `docs/03` §6 (V-14).
- [x] Historical term data is preserved. — `test_historical_offering_is_immutable`: PATCH/DELETE on past-term offering → 409 `CONFLICT`, data unchanged; `AcademicTerm` rows never overwritten (append-only per `docs/17`).
- [x] APIs are documented and tested. — 132 backend tests green (SQLite + regression test); OpenAPI regenerated (`openapi.yaml`, 50 paths, `spectacular --validate` clean); live-tested against compose (table below).
- [x] Prerequisite relation works. — bidirectional edges (`prerequisite_edges`/`dependent_edges`), nested admin CRUD + self-edge & duplicate guards (409), nested read on `/courses/`.

## Verification record (2026-10-18)

| Gate | Command | Result |
|---|---|---|
| Backend tests (SQLite) | `pytest` | 132 passed |
| Lint | `ruff check .` | All checks passed |
| System check | `manage.py check` (DEBUG=false) | 0 issues |
| Migrations | `makemigrations --check --dry-run` | No changes detected |
| Contract | `spectacular --file openapi.yaml --validate` | exit 0, 50 paths (was 1) |
| Frontend | `typecheck` / `vitest` / `build` | 0 errors / 23 passed / 269 kB |
| Live health | `GET /api/v1/health/` (compose, PostgreSQL) | `database: ok` |
| Live reads (student JWT) | `/courses/`, `/course-offerings/`, `/professors/`, `/terms/`, `/calendar/events/`, `/exams/`, `/announcements/`, `/students/me/`, `/students/planner/` | all 200 |
| Live search | `GET /courses/?search=برنامه` (Persian + trgm) | 200 |
| Live admin CRUD | create → 201, duplicate → 409, delete → 204, re-delete → 404 envelope | pass |
| Live permissions | student → admin route 403, anon → 401, anon → `/courses/` 401 | pass |
| Live validation | POST missing fields → 400 `VALIDATION_ERROR` with Persian per-field details | pass |
| Seed | `manage.py seed --data-dir /data` | 421 prerequisites, 278 offerings, 350 schedules, 155 exams, 28 professors, 3 demo accounts |

### Bugs found by this phase's verification (all fixed + regression-tested)
1. **Test suite hung on DB tests** — pytest-django imports settings *before* root `conftest.py` runs, so `backend/.env`'s `DATABASE_URL` (copied in this phase) was frozen into `DATABASES` and the suite waited forever on a down Postgres. Fix: order-independent guard in `config/environment.py` (skips `.env` `DATABASE_URL` under pytest, honours `TEST_DATABASE_URL`); CI path verified.
2. **View-level 404 crashed the shared error handler → 500** — DRF converts `Http404`→`NotFound` only internally; `_translate` got the raw object without `.detail`. Fix: normalize in `_translate`; regression test added.
3. **English `message` leaked** — DRF's internal detail strings ("No Course matches the given query.") bypassed Persian localization. Fix: `_message_from_detail` passes through only Persian text; regression asserted.
4. **`manage.py seed` unusable in the container** — `data/` wasn't mounted. Fix: read-only `./data:/data` volume in `docker-compose.yml`.

## Known limitations
- Admin update/delete of **professors/terms/exams/announcements/users** was exercised only through unit tests, not the live script (courses + offerings were live-tested).
- `Enrollment`/planner endpoints are minimal (Phase 06 expands UX; Phase 11 owns eligibility semantics).
- No Postgres-backed test run in this session (Docker was needed for live tests, but the pytest suite itself ran on SQLite; CI covers PostgreSQL).
- Seed dataset lives outside the container by default; compose now mounts it read-only — bare-metal runs still use `<repo root>/data`.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.
