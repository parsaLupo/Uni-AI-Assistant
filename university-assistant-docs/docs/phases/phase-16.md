# Phase 16 — Deployment, Observability & Release

## Objective

Make the application deployable as a **local production-like stack** for
university demonstrations, with a reproducible setup, a controlled migration
step, backups, a tested restore, health probes, smoke tests and a rehearsed
rollback.

**Scope decision (explicit).** Phase 16 targets a personal laptop / demo
machine at `http://localhost:8080`. Public/VPS deployment, a domain name and
HTTPS termination are **out of scope for this phase** and are recorded as
deferred below. The original checklist also asked for Prometheus dashboards and
alerting; that was evaluated and deliberately not added (see
[Monitoring decision](#monitoring-decision-deferred)).

## Tasks

- production Docker configuration
- reverse proxy / HTTPS
- environment configuration
- database migration process
- backups
- health checks
- logging
- smoke tests
- release documentation

## Acceptance criteria

- [x] The stack starts from the documented steps alone (verified on a clean,
      isolated Compose project).
- [ ] HTTPS is enabled. **Deferred** — local HTTP-only scope; see
      [Deviations](#deviations-from-the-original-checklist).
- [x] Database backup exists and restore is tested (real restore drill, below).
- [x] Health endpoints are implemented and wired to Docker health checks; an
      induced dependency failure changes readiness/deep health. External
      alerting is deferred with monitoring.
- [x] Smoke tests pass after deployment (31/31).
- [x] Rollback is documented and rehearsed.
- [x] Release documentation exists (`DEPLOYMENT.md`, rewritten `README.md`).

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

---

## Execution record (Phase 16 — local production-ready release)

### Architecture delivered

```text
Browser ──► nginx (web, host :8080)
              ├── /            React production build (static)
              ├── /api/…       Django + Gunicorn (private network)
              └── /health/…    Django probes
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
          PostgreSQL 16 + pgvector         Redis ──► Celery worker
          (named volume pgdata)            (private network)
```

- `docker-compose.yml` defines five services: `db`, `redis`, `backend`,
  `worker`, `web`. Only `web` publishes a host port (`${APP_PORT}:80`).
- Backend image: Gunicorn (`docker/gunicorn.conf.py`), non-root `app` user,
  `config.release_check` gate in the entrypoint, no migrations at start.
- Frontend image: multi-stage `node:22-alpine` build → `nginx:1.27-alpine`,
  non-root runtime, SPA fallback, gzip, static asset caching, security headers.
- PostgreSQL, Redis and uploaded media live in named volumes and survive
  `docker compose down` (only `down -v` deletes them).

### What was implemented

**Release stack** — `docker-compose.yml`, `backend/Dockerfile`,
`frontend/Dockerfile`, `frontend/nginx.conf`, `docker/gunicorn.conf.py`,
`docker/entrypoint.sh`, `docker-compose.dev.yml` (kept development overlay),
`docker-compose.e2e.yml` updated.

**Configuration and startup validation** — `.env.example` documents every
variable; `backend/config/release_check.py` refuses to start with DEBUG on,
short/placeholder secrets, a non-PostgreSQL `DATABASE_URL`, weak DB password,
missing/inconsistent cookie and HTTPS flags, Celery eager mode, an unspecified
AI provider, or a weak demo password. Only variable names/reasons are printed,
never values. `backend/config/environment.py` requires PostgreSQL + pgvector;
there is no SQLite fallback.

**Controlled migrations** — migrations are a separate `docker compose run --rm
backend python manage.py migrate --noinput` step, never part of the container
command. `deploy-local.ps1` performs build → wait for DB → migrate → seed →
start → wait ready → tag rollback images.

**Health probes** — `/health/live` (no dependency access), `/health/ready`
(PostgreSQL), `/health/deep` (database, Redis, Celery worker, media storage, AI
provider configuration). Root aliases exist for the proxy; the versioned API
keeps `/api/v1/health/`. Root aliases are excluded from the OpenAPI contract,
which still contains only `/api/v1/…` paths. Responses expose coarse states and
latencies only, never DSNs, paths or driver errors.

**Observability** — structured access logs with request id, method, path,
status and latency; `X-Request-ID` accepted/propagated from nginx; AI provider
outcomes and Celery ingestion stages/failures logged in the same format, with
the request id propagated into the document-processing task. Docker health
checks surface container state in `docker compose ps`.

**Backups / restore** — `scripts/backup.ps1` runs `pg_dump --format=custom`,
validates the archive with `pg_restore --list`, copies it to the host
`backups/` directory (gitignored) with a timestamp, and prunes by
`BACKUP_RETENTION_DAYS`. `scripts/restore.ps1` takes a safety backup, requires
typing the database name unless `-Force`, restores with
`--clean --if-exists --exit-on-error`, and verifies core tables.
`scripts/restore-drill.ps1` restores into a temporary database, compares row
counts, runs a real Django ORM query through the backend image, writes evidence
to `local/` and drops the temporary database.

**Demo data** — `seed_demo` (guarded by `DEMO_MODE=true`) creates four
reserved `@semnan.local` identities, one welcome notification and, when the
official dataset has no past term, a clearly demo-only previous term with three
passed courses so the dashboard and selection screens have content. It is
idempotent and lives only in the demo command; the normal `seed` path never
creates demo identities.

**Release tooling** — `scripts/init-env.ps1` (random secrets, no overwrite),
`deploy-local.ps1`, `smoke-test.ps1`, `backup.ps1`, `restore.ps1`,
`restore-drill.ps1`, `rollback-rehearsal.ps1`, `secret-scan.ps1`,
`show-demo-credentials.ps1`, `test-backend.ps1` (disposable PostgreSQL +
pgvector container), shared `_common.ps1`.

**Documentation** — new root `DEPLOYMENT.md` (prerequisites, manual and scripted
setup, URLs, demo accounts, environment table, migrations, backup/restore,
health, observability, smoke tests, browser verification, rollback, shutdown,
demo reset, verification commands, known limitations, troubleshooting,
release checklist); rewritten root `README.md`; deployment doc updated;
`START-HERE.md` marks Phase 16 as the current final phase.

### Verification evidence

All checks below were run on the actual code in this working tree.

| Check | Command | Result |
|---|---|---|
| Backend suite | `scripts/test-backend.ps1` (disposable `pgvector/pgvector:0.8.6-pg16`) | **618 passed**, 12 subtests, 176 warnings, 383.15 s |
| Backend lint | `python -m ruff check .` | clean |
| Migration drift | `manage.py makemigrations --check --dry-run` | `No changes detected` |
| Frontend unit tests | `npm run test` | **116 passed** in 19 files |
| TypeScript | `npm run typecheck` | clean |
| Production build | `npm run build` | success (`dist/index.html`, CSS 43.36 kB, JS 570.56 kB) |
| Compose validation | `docker compose config --quiet` | OK |
| Image build | `deploy-local.ps1` | backend + web built and started |
| Secret scan | `scripts/secret-scan.ps1` | clean: tracked files, full Git history, sensitive tracked files, ignore rules |
| Fresh deployment | `deploy-local.ps1 -EnvFile .env.fresh -ProjectName usa-phase16-fresh` (port 18080) | 5/5 services healthy; migrate + seed_demo succeeded |
| Smoke tests | `scripts/smoke-test.ps1 -BaseUrl http://localhost:18080 …` | **31/31 passed** (`local/smoke-test-fresh-*.log`) |
| Restore drill | `scripts/restore-drill.ps1 …` | backup 0.16 MB, restored into temp DB, row counts match, ORM query OK |
| Rollback rehearsal | `scripts/rollback-rehearsal.ps1 …` | missing tag fails visibly; recorded image returns backend to ready |
| Browser | in-app Chromium against `http://localhost:18080` | student + admin journeys verified |

#### Restore drill detail

```text
Verified 'usa_db_restore_drill': courses=1131 users=4 enrollments=5
table courses_course:            source=1131 restored=1131 match=True
table courses_courseoffering:    source=281  restored=281  match=True
table accounts_user:             source=4    restored=4    match=True
table academics_academicterm:    source=2    restored=2    match=True
table students_enrollment:       source=5    restored=5    match=True
restore: ok
```

The temporary database was dropped afterwards; the primary database was never
modified.

#### Induced-failure behaviour

| Failure | `/health/live` | `/health/ready` | `/health/deep` | Frontend |
|---|---|---|---|---|
| PostgreSQL stopped | 200 | **503** | **503** | 200 |
| Celery worker stopped | 200 | 200 | **503** | 200 |
| Backend stopped | 502 (nginx) | 502 | 502 | **200** |
| Invalid Groq key | 200 | 200 | 200 (AI is optional) | 200 |

With an invalid provider key, `/api/v1/ai/ask/` returned
`HTTP 503 {"error":{"code":"AI_PROVIDER_ERROR","message":"سرویس هوش مصنوعی موقتاً در دسترس نیست.","details":{}}}` —
a safe Persian message with no provider internals — while liveness stayed 200.

#### Browser verification (production build, not Vite dev server)

- Student login → dashboard: current term, 6 planned units, 2 upcoming exams,
  notifications, current-term courses.
- Course selection by code `1916003`: deterministic `ALREADY_PASSED` result
  with Persian explanation, unit arithmetic and rule-engine version.
- Course selection by Persian name `ریاضی مهندسی`: ambiguity list with three
  real offerings; selecting one returned `ALREADY_PLANNED` +
  `SCHEDULE_CONFLICT` with a grounded explanation.
- Assistant: asked for the prerequisite of a course; answered from structured
  data (`STRUCTURED`, no invented prerequisite) and stored the conversation.
- Admin login → `/admin`: real counts (4 users, 1131 courses, 61 professors),
  AI request metrics, health status.
- `/admin/users`: 4 seeded accounts with roles and status.
- Hard reload of `/admin/users`, `/assistant`, `/announcements`: all served by
  nginx and rendered by the SPA with no console errors (the only console entry
  is the expected `401/403` refresh probe before login).

### Deviations from the original checklist

| Original item | Status | Reason |
|---|---|---|
| HTTPS + HTTP→HTTPS redirect + HSTS | **Deferred** | Phase scope is local HTTP only. The flags exist (`COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_PROXY_SSL_HEADER`) and `DEPLOYMENT_MODE=release` requires them, so a future TLS deployment cannot silently inherit local values. |
| Prometheus `/metrics`, dashboards, SLOs | **Deferred** | No metrics endpoint exists; adding `django-prometheus` would be a new infrastructure/runtime dependency not justified for a single-laptop demo. Structured logs + health probes + Docker health cover the scope. |
| Alerting on error rate / provider failure | **Deferred** | No alerting target on a local machine. Failures are visible in `docker compose ps` and logs; `/health/deep` reports provider state. |
| Automated, off-host backups | **Partial** | Backups are timestamped, validated, retention-pruned and written outside the container, but scheduling/off-host shipping is manual. Documented as a limitation and a release-checklist step. |
| Base images pinned by digest | **Not done** | Images are pinned by version tag (`python:3.13-slim`, `node:22-alpine`, `nginx:1.27-alpine`, `pgvector/pgvector:0.8.6-pg16`, `redis:7.4-alpine`) for reproducibility; digest pinning would need an update process that this phase does not have. |
| Commit-tagged images / checkpoint commit | **Partial** | `deploy-local.ps1` tags `rollback-<timestamp>` images; no commit or tag was created because committing/pushing was not authorised. |

### Monitoring decision (deferred)

Prometheus/Grafana were evaluated and **not** added. The backend has no
`/metrics` endpoint, the deployment is a single host with no alert receiver, and
the user scope forbids unnecessary infrastructure. The proportionate substitute
is: structured request/task/provider logs, request-id correlation, three health
probes, and Docker health status. If a public deployment is approved later, add
a metrics endpoint and a separate `docker-compose.monitoring.yml` profile; the
application does not depend on monitoring.

### D1–D7 review (touched areas)

- **D1 API health/quality** — all consumer paths remain under `/api/v1/`; root
  health aliases are excluded from OpenAPI. Error envelopes, status codes and
  serializers unchanged. Health responses leak no internals.
- **D2 Persian/RTL** — all new user-facing text is Persian/RTL; demo and
  selection output uses Persian numerals/Jalali dates.
- **D3 Security** — no secret in repo or history (scan clean); `.env` ignored;
  release entrypoint rejects insecure defaults; provider key stays server-side;
  logs contain no tokens/passwords.
- **D4 Observability** — request id, method, path, status, latency; correlation
  id propagated into Celery ingestion; AI and ingestion outcomes logged.
  Metrics/alerts explicitly deferred above.
- **D5 Testing/evidence** — 618 backend tests, 116 frontend tests, typecheck,
  build, Ruff, migration check, smoke, restore drill, rollback rehearsal.
- **D6 Accessibility/UI** — no UI redesign in this phase; the verified screens
  have labelled inputs, loading/empty/error states and keyboard-operable forms.
- **D7 Data integrity** — demo history is additive and idempotent, never
  overwrites records; migrations unchanged; restore preserves row counts.

### Migrations

- No model changes; `makemigrations --check --dry-run` reports no drift.
- Migrations are applied as a separate, controlled release step.

### Files changed (Phase 16 scope)

- Compose/images/proxy: `docker-compose.yml`, `docker-compose.dev.yml`,
  `docker-compose.e2e.yml`, `backend/Dockerfile`, `backend/docker/`,
  `frontend/Dockerfile`, `frontend/nginx.conf`.
- Configuration/health/logging: `.env.example`, `backend/config/settings.py`,
  `backend/config/urls.py`, `backend/config/release_check.py`,
  `backend/apps/common/views.py`, `backend/apps/common/urls.py`,
  `backend/apps/documents/{services,tasks,views}.py`, `backend/conftest.py`,
  `backend/requirements.txt`, `.gitignore`.
- Demo seed: `backend/apps/common/seed_data.py`,
  `backend/apps/common/management/commands/seed_demo.py`.
- Tests: `backend/apps/common/tests/test_health_probes.py`,
  `test_release_check.py`, `test_seed_demo.py`.
- Tooling: `scripts/` (`init-env`, `deploy-local`, `smoke-test`, `backup`,
  `restore`, `restore-drill`, `rollback-rehearsal`, `secret-scan`,
  `show-demo-credentials`, `test-backend`, `_common`).
- Documentation: `DEPLOYMENT.md`, `README.md`, `START-HERE.md`,
  `docs/09-deployment.md`, this record.

Unrelated in-progress work present in the same working tree (course lookup by
Persian name, student/document adjustments) was **not** reverted or folded into
Phase 16; it is reported separately in the task report.

### Known limitations

- Local HTTP only: no TLS, domain, HSTS or public exposure.
- Single host, single backend replica, no load balancer or shared object
  storage; uploads live in the `media_data` volume.
- Backups are manual, not scheduled or shipped off-host.
- No external metrics/alerting (decision above).
- Demo content depends on the bundled Semnan University dataset.
- Default `.env.example` uses `AI_PROVIDER=mock`; a real Groq key is required
  for real-provider demonstrations.
- Helper scripts are PowerShell; raw Docker commands are portable.
- Migrations are forward-only in practice; roll back with a pre-release
  database backup (documented).

### Acceptance criteria status

- [x] Production environment starts from the documented steps alone.
- [ ] HTTPS — **deferred** (local HTTP-only scope, documented).
- [x] Database backup exists and a restore was tested.
- [x] Health endpoints exist, are wired to Docker health, and were verified
      under induced dependency failure; external alerting deferred.
- [x] Smoke tests pass after deployment (31/31).
- [x] Rollback documented and rehearsed.

**Phase status: DONE for the approved local-demo scope**, with HTTPS, external
monitoring/alerting and off-host scheduled backups explicitly deferred and
documented. No later phase has been started.
