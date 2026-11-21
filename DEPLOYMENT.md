# Local Deployment Runbook — University Smart Assistant

This is the operational guide for the **Phase 16 local production-like stack**.
It is written for someone who has never worked on this repository.

> **Scope.** This deployment is for a personal laptop, university demos and
> professor presentations. It runs on `http://localhost:8080` over HTTP. It is
> **not** a public/VPS deployment: no domain, no TLS certificate, no external
> alerting. See [Known limitations](#17-known-limitations).

The stack is:

```text
Browser ──► nginx (web, host :8080)
              ├── /            React production build (static files)
              ├── /api/…       Django + Gunicorn (backend, private network)
              └── /health/…    Django health probes
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
          PostgreSQL + pgvector            Redis ──► Celery worker
          (db, named volume)               (private network)
```

Only `web` publishes a host port. PostgreSQL, Redis, Django and Celery stay on
the private Compose network.

---

## 1. Prerequisites

| Requirement | Version / notes |
|---|---|
| Docker Desktop (Windows/macOS) or Docker Engine + Compose v2 | Compose v2.20+ (`docker compose`, not `docker-compose`) |
| RAM | 8 GB recommended (4 GB minimum for the demo) |
| Disk | ~2 GB for images + database + uploads |
| Free host port | `8080` by default (`APP_PORT` in `.env`) |
| PowerShell | PowerShell 7 recommended for the helper scripts; the raw Docker commands below are portable |

Verify:

```powershell
docker version
docker compose version
```

---

## 2. First-time setup

From the repository root:

```powershell
# 1. Create the local environment file with random secrets.
scripts/init-env.ps1

# 2. Build, migrate, seed demo data, start everything, wait for readiness.
scripts/deploy-local.ps1
```

`init-env.ps1` copies `.env.example` to `.env` (gitignored) and replaces the
three `__CHANGE_ME__` placeholders with unique random values:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DEMO_PASSWORD`

It never prints the values. It refuses to overwrite an existing `.env` unless
you pass `-Force`.

`deploy-local.ps1` performs these steps and stops on the first failure:

1. build the backend and web images;
2. start PostgreSQL and Redis and wait for `pg_isready`;
3. run migrations as a **separate** controlled step;
4. run `seed_demo` (idempotent) to load the real academic dataset and demo
   accounts;
5. start the full stack;
6. wait for `http://localhost:8080/health/ready/`;
7. tag the working images as `rollback-<timestamp>` and record the tag in
   `local/last-rollback-tag.txt` (gitignored).

### Manual equivalent (portable, no PowerShell scripts)

```bash
cp .env.example .env
# Edit .env and replace every __CHANGE_ME__ placeholder.
# Generate values with: openssl rand -base64 48   (or any password manager)

docker compose up -d --build db redis
docker compose run --rm backend python manage.py migrate --noinput
docker compose run --rm backend python manage.py seed_demo
docker compose up -d --build
```

`docker compose up -d --build` on its own starts the containers, but migrations
are deliberately **not** run at container start. A fresh database has no schema
until step 3 completes. This is what makes migrations a controlled release
step instead of a race between replicas.

Check readiness:

```bash
curl http://localhost:8080/health/ready/
```

---

## 3. URLs

| Purpose | URL |
|---|---|
| Application (demo entry point) | <http://localhost:8080> |
| Student dashboard | <http://localhost:8080/dashboard> |
| Admin area | <http://localhost:8080/admin> |
| Course selection assistant | <http://localhost:8080/selection> |
| AI assistant | <http://localhost:8080/assistant> |
| Versioned API health | <http://localhost:8080/api/v1/health/> |
| Liveness | <http://localhost:8080/health/live/> |
| Readiness | <http://localhost:8080/health/ready/> |
| Deep dependency health | <http://localhost:8080/health/deep/> |
| OpenAPI UI | <http://localhost:8080/api/v1/schema/swagger-ui/> |
| OpenAPI schema | <http://localhost:8080/api/v1/schema/> |

If `APP_PORT` is changed in `.env`, replace `8080` with that value.

---

## 4. Demo accounts

All four accounts share the value of `DEMO_PASSWORD` from your local `.env`:

| Role | Email |
|---|---|
| SUPERADMIN | `root@semnan.local` |
| ADMIN | `admin@semnan.local` |
| STUDENT | `student@semnan.local` |
| PROFESSOR | `professor@semnan.local` |

Print the credentials from the gitignored `.env` **on your machine only**:

```powershell
scripts/show-demo-credentials.ps1
```

Never commit, screenshot, or paste this output into an issue or chat. The
accounts exist only after `seed_demo` has run with `DEMO_MODE=true`.

`seed_demo` is idempotent:

```bash
docker compose run --rm backend python manage.py seed_demo
```

- Re-running does not duplicate users, courses, offerings, enrollments or
  notifications.
- It resets the four reserved `@semnan.local` passwords to `DEMO_PASSWORD`
  unless `--keep-passwords` is passed.
- It adds a small, clearly demo-only past term with three passed courses and
  one welcome notification so the dashboard and course-selection screens have
  content. This is isolated in the dedicated demo command; the normal `seed`
  workflow never creates demo identities.
- `--skip-history` skips the passed courses and notification.

The real academic dataset comes from `data/` (`courses.json`,
`course-offering.json`, `Professors.json`, …). Those files are read-only inputs
and are mounted at `/data` in the backend container.

---

## 5. Environment configuration

`.env.example` documents every supported variable. The most important ones:

| Variable | Purpose | Local-demo value |
|---|---|---|
| `DEPLOYMENT_MODE` | `local-demo` (HTTP) or `release` (HTTPS) | `local-demo` |
| `APP_PORT` | Host port for nginx | `8080` |
| `IMAGE_TAG` | Local image tag / rollback tag | `local` |
| `DJANGO_SECRET_KEY` | Django/JWT signing key, ≥32 chars | random |
| `DJANGO_DEBUG` | Must be `false` in the release stack | `false` |
| `ALLOWED_HOSTS` | Accepted Host headers | `localhost,127.0.0.1` |
| `POSTGRES_DB/USER/PASSWORD` | PostgreSQL identity | `usa_db` / `usa_user` / random |
| `COOKIE_SECURE` | Secure cookies (needs HTTPS) | `false` |
| `SECURE_SSL_REDIRECT` | Force HTTPS | `false` |
| `SECURE_HSTS_SECONDS` | HSTS lifetime | `0` |
| `AI_PROVIDER` | `mock` or `groq` | `mock` |
| `AI_PROVIDER_API_KEY` | Groq key when `AI_PROVIDER=groq` | empty for mock |
| `DEMO_MODE` | Allows `seed_demo` | `true` |
| `DEMO_PASSWORD` | Shared demo password, ≥10 chars, not the old public value | random |
| `BACKUP_RETENTION_DAYS` | Local backup pruning | `14` |
| `GUNICORN_WORKERS/THREADS` | Gunicorn sizing | `3` / `2` |

The backend container entrypoint runs `python -m config.release_check` before
Gunicorn or Celery starts. It refuses to boot when:

- `DJANGO_DEBUG` is not `false`;
- the Django secret is short, a known placeholder, or the development value;
- `ALLOWED_HOSTS` is empty;
- `DATABASE_URL` is not PostgreSQL or carries a weak password;
- `COOKIE_SECURE` / `SECURE_SSL_REDIRECT` / `SECURE_HSTS_SECONDS` are missing or
  inconsistent with the deployment mode;
- Celery is in eager mode;
- `AI_PROVIDER` is not explicitly `mock` or `groq`, or `groq` has no key;
- `DEMO_MODE=true` but `DEMO_PASSWORD` is weak or reuses the old public value.

Only variable names and short reasons are printed; values are never echoed.
Failures are visible in `docker compose logs backend`.

### Using a real Groq key

```powershell
scripts/init-env.ps1 -AiProvider groq -AiKey '<your-key>'
scripts/deploy-local.ps1
```

Or edit `.env`:

```dotenv
AI_PROVIDER=groq
AI_PROVIDER_API_KEY=gsk_...
AI_MODEL=
```

`AI_MODEL` may stay empty to use the adapter's pinned default. The key is read
only by Django; it is never sent to the browser or baked into the frontend
image. Use `mock` for offline demos and deterministic CI.

---

## 6. Database migrations

Migrations are a **separate release step**, never part of the backend
container command:

```bash
docker compose run --rm backend python manage.py migrate --noinput
```

- `docker compose run` waits for the `db` health check, applies migrations in a
  one-off container, prints the result, and exits.
- A failure is visible in the command output and does not get silently retried
  by a restarting web container.
- `docker compose up -d` does not migrate. Run the command after pulling a
  release that contains new migration files.
- The PostgreSQL named volume `pgdata` persists across `docker compose down`.

Check for missing migrations during development:

```bash
docker compose run --rm backend python manage.py makemigrations --check --dry-run
```

---

## 7. Backups

Backups use PostgreSQL's native `pg_dump` custom format and are written outside
the container filesystem.

```powershell
scripts/backup.ps1
scripts/backup.ps1 -OutDir D:\Backups\usa
```

The script:

1. verifies PostgreSQL is reachable;
2. runs `pg_dump --format=custom --no-owner --no-acl` inside the `db`
   container (credentials come from the container environment; no password is
   printed or placed on a command line);
3. validates the archive with `pg_restore --list`;
4. copies it to the host as `backups/<db>_<YYYYmmdd_HHMMSS>.dump`;
5. prunes files older than `BACKUP_RETENTION_DAYS` (default 14).

`backups/` is gitignored. Keep a copy on external storage for anything you
cannot afford to lose.

Manual equivalent:

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --file /tmp/usa.dump'
docker compose cp db:/tmp/usa.dump "backups/usa_db_$(date +%Y%m%d_%H%M%S).dump"
docker compose exec -T db rm -f /tmp/usa.dump
```

---

## 8. Restore

### 8.1 Restore drill (safe, primary database untouched)

```powershell
scripts/restore-drill.ps1
```

This creates a fresh backup, restores it into a temporary database
(`usa_db_restore_drill`), compares row counts for critical tables, runs a real
Django ORM query through the backend image against the restored copy, writes
evidence to `local/restore-drill-<timestamp>.txt` (gitignored), and drops the
temporary database. The primary database is never modified.

### 8.2 Restore into an isolated database

```powershell
scripts/restore.ps1 -BackupFile backups/usa_db_20260101_120000.dump `
  -TargetDatabase usa_db_restore_check -CreateIfMissing
```

Use this to inspect an old backup without touching the live demo database.

### 8.3 Restore the live database (destructive)

```powershell
scripts/restore.ps1 -BackupFile backups/usa_db_20260101_120000.dump
```

The script:

- warns that the live database will be replaced;
- requires you to type the exact database name (or pass `-Force` for
  automation);
- takes a safety backup first;
- terminates open connections, restores with `--clean --if-exists
  --exit-on-error`;
- verifies `courses_course`, `accounts_user` and `students_enrollment` exist
  and prints their counts.

Stop the backend/worker first if you want to avoid reconnects during a long
restore:

```bash
docker compose stop backend worker
scripts/restore.ps1 -BackupFile backups/<file>.dump
docker compose start backend worker
```

---

## 9. Health checks

| Endpoint | Meaning | Used by |
|---|---|---|
| `/health/live` | Process is alive; no dependency access | Manual / future orchestrator |
| `/health/ready` | Django can reach PostgreSQL; 503 otherwise | Compose health check for `backend` |
| `/health/deep` | Database, Redis, Celery worker, media storage, AI provider configuration | Manual verification |

`/health/deep` returns `200` only when the required dependencies are healthy.
The AI provider is reported as `mock`, `configured` or `not_configured`; an
optional provider never makes the whole service unhealthy. Responses contain
coarse states and timings only — no DSNs, paths or driver errors.

Useful commands:

```bash
docker compose ps
docker compose logs --tail 100 backend
docker compose logs --tail 100 worker
docker compose logs --tail 100 web
```

---

## 10. Observability

The local stack intentionally uses the tools already present:

- **Structured request logs** on stdout: `request_id`, method, path, status,
  latency. Request ids are generated by middleware and forwarded by nginx
  (`X-Request-ID`).
- **Application logs** for AI outcomes/provider failures and Celery ingestion
  stages/failures, in the same format.
- **Health endpoints** expose database/Redis/worker/storage availability.
- **Docker health checks** mark unhealthy containers in `docker compose ps`.

```bash
docker compose logs -f backend worker
docker compose logs --since 30m backend | Select-String 'level=ERROR'
```

### Prometheus/Grafana evaluation (DEFERRED)

Prometheus and Grafana were evaluated and deliberately **not** added:

- the backend has no `/metrics` endpoint, so adding Prometheus would require a
  new runtime dependency and a new exposition surface;
- the demonstration runs on one laptop with no alerting target;
- logs + health probes + Compose health status cover the Phase 16 local scope;
- the user scope explicitly forbids unnecessary infrastructure.

If a future public deployment needs dashboards, add a metrics endpoint and a
separate `docker-compose.monitoring.yml` profile then. The main application
does not depend on monitoring.

---

## 11. Smoke tests

Run against the actual running production-like stack:

```powershell
scripts/smoke-test.ps1
scripts/smoke-test.ps1 -BaseUrl http://localhost:18080 -ProjectName usa-phase16-fresh
```

It verifies:

- live/ready/deep health and the versioned API health;
- the frontend root and direct SPA routes (`/selection`, `/admin/users`,
  `/assistant`) return `index.html`;
- student, admin and professor logins;
- `/auth/me` and a student read endpoint;
- admin-only access is allowed for an admin and denied (`403`) for a student;
- course selection by code and by Persian name;
- notifications and a new conversation survive a backend restart;
- a grounded AI answer;
- backend/worker logs contain no `Traceback` / `level=ERROR`.

The script prints the configured AI provider. With `AI_PROVIDER=mock` the AI
check is explicitly a **mock-provider** check, not a real external LLM call.
With `AI_PROVIDER=groq` it also asks a general question that exercises the real
provider. Never present a mock run as real-provider verification.

Useful flags: `-SkipAI`, `-SkipPersistenceRestart`.

---

## 12. Browser verification

The critical student and admin workflows are verified in a real browser against
`http://localhost:8080` (not the Vite dev server): login, dashboard, course
selection, assistant, notifications, admin user list, and direct-route refresh.
Evidence is recorded in the Phase 16 verification report.

---

## 13. Rollback

### 13.1 Roll back the application images

`deploy-local.ps1` tags every successful deployment:

```text
university-assistant-backend:rollback-20260101_120000
university-assistant-web:rollback-20260101_120000
```

The latest tag is in `local/last-rollback-tag.txt` (gitignored).

```powershell
$tag = Get-Content local/last-rollback-tag.txt
$env:IMAGE_TAG = $tag
docker compose up -d --no-build backend worker web
```

Then verify:

```bash
curl http://localhost:8080/health/ready/
```

### 13.2 Roll back the source

```bash
git log --oneline
git checkout <previous-working-commit>
docker compose build
docker compose up -d
```

Never rewrite history to roll back; create a revert commit or check out a known
checkpoint. Do not push without explicit permission.

### 13.3 Roll back the database

If a release changed data or applied an incompatible migration, restore the
backup taken before the release:

```powershell
scripts/restore.ps1 -BackupFile backups/<pre-release>.dump
```

### 13.4 Migration compatibility limitation

Django migrations are usually forward-only. A code rollback does **not**
automatically reverse a schema migration. Options, in order of safety:

1. restore the pre-release database backup (recommended);
2. run `python manage.py migrate <app> <previous-migration>` only when the
   migration is explicitly reversible and you have verified it on a copy;
3. keep the newer schema and roll back only application code if the old code is
   compatible with the new columns.

The release process therefore takes a backup **before** migrating.

### 13.5 Rehearsal

```powershell
scripts/rollback-rehearsal.ps1
```

It proves that a missing image tag fails visibly and that the recorded previous
image brings the backend back to ready. It changes no data.

---

## 14. Shutdown and restart

```bash
docker compose down          # stop and remove containers; volumes are kept
docker compose up -d         # start again with the same data
```

Do **not** use `docker compose down -v` unless you intend to delete the
database, uploads and Redis data. There is no undo for `-v`.

Check what is running:

```bash
docker compose ps
```

---

## 15. Resetting demo data safely

### Normal refresh (non-destructive, idempotent)

```bash
docker compose run --rm backend python manage.py seed_demo
```

### Full demo reset (destructive — demo database only)

Only do this when the database contains demo data you are willing to lose.

```powershell
# 1. Back up first.
scripts/backup.ps1

# 2. Stop the stack.
docker compose down

# 3. Remove ONLY the PostgreSQL volume (keep media_data and redisdata).
docker volume ls | Select-String 'university-assistant_pgdata'
docker volume rm university-assistant_pgdata

# 4. Recreate schema and demo data.
docker compose up -d db redis
docker compose run --rm backend python manage.py migrate --noinput
docker compose run --rm backend python manage.py seed_demo
docker compose up -d
```

The exact volume name depends on the Compose project name; confirm it with
`docker volume ls` before removing anything.

---

## 16. Verification commands

```powershell
# Backend: lint + full suite against disposable PostgreSQL + pgvector
cd backend
.\.venv\Scripts\python.exe -m ruff check .
cd ..
scripts/test-backend.ps1

# Frontend: unit tests, typecheck, production build
cd frontend
npm run test
npm run typecheck
npm run build
cd ..

# Compose validation and image build
docker compose config --quiet
docker compose build

# Repository secret scan (tracked files + Git history + ignore rules)
scripts/secret-scan.ps1
```

Expected results at the Phase 16 checkpoint:

- backend: `618 passed` (plus 12 subtests) against PostgreSQL;
- frontend: `116 passed` in 19 files;
- `ruff check .`: clean;
- TypeScript: clean;
- `vite build`: succeeds;
- `docker compose config --quiet`: succeeds;
- secret scan: clean.

---

## 17. Known limitations

- **Local HTTP only.** No TLS, domain, HSTS or public exposure. `DEPLOYMENT_MODE`
  and the transport flags are explicit so a future HTTPS deployment cannot
  silently inherit these values.
- **Single host, single backend replica.** No horizontal scaling, load balancer
  or shared object storage. Uploaded documents live in the `media_data` volume.
- **Backups are manual.** `scripts/backup.ps1` is not scheduled. Run it before
  every release and before any destructive operation.
- **No external monitoring/alerting.** Logs and health endpoints only.
- **Demo data is local.** Demo identities and the demo past term are created
  only by `seed_demo` with `DEMO_MODE=true`; they are not part of the normal
  production seed path.
- **AI provider may be mock.** The default `.env.example` uses `AI_PROVIDER=mock`
  for offline demos. Set `groq` and a key for real-provider demonstrations.
- **Dataset-dependent demo content.** Course selection examples depend on the
  bundled Semnan University dataset; course codes/names may differ from another
  university's data.
- **Windows scripts.** The helper scripts are PowerShell. The raw Docker
  commands in this document work on any OS.
- **No automatic migration on start.** This is intentional; run the documented
  migration command after pulling changes.

---

## 18. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `DJANGO_SECRET_KEY must be set` | `.env` is missing or still has `__CHANGE_ME__`. Run `scripts/init-env.ps1` (or replace placeholders manually). |
| `release-config: refusing to start` | The entrypoint rejected an insecure value. Read the variable names in the message (values are never printed), fix `.env`, then `docker compose up -d`. |
| `port is already allocated` | Another process uses `8080`. Set `APP_PORT=8081` in `.env` and `docker compose up -d`. |
| `db` is unhealthy | Check `docker compose logs db`; a changed `POSTGRES_PASSWORD` does not alter an existing volume. Restore the original password or reset the demo database (section 15). |
| `backend` restarts / 502 from nginx | Read `docker compose logs backend`. Common causes: migrations not applied, invalid `.env`, database not ready. |
| `worker` unhealthy | Check Redis (`docker compose logs redis`) and `docker compose logs worker`. |
| Login fails after changing `DEMO_PASSWORD` | Re-run `seed_demo` to rotate the reserved demo accounts, or use the old password. |
| AI answer fails | Check `AI_PROVIDER` and key. With `groq`, verify the key and network. Failures must degrade gracefully, not crash the API. |
| `migrate` fails | The command exits non-zero and prints the failing migration. Fix the cause, restore a backup if needed, then rerun. Do not ignore it. |
| Frontend route 404 after refresh | nginx should serve `index.html` for SPA routes. Confirm the `web` image is the current build: `docker compose build web && docker compose up -d web`. |
| `docker compose build` cannot reach the registry | Retry on a working network; images are pinned (`python:3.13-slim`, `node:22-alpine`, `nginx:1.27-alpine`, `pgvector/pgvector:0.8.6-pg16`, `redis:7.4-alpine`). |
| Secret scan flags a file | Do not rewrite history automatically. Rotate the credential, remove it from the working tree, and report the history risk. |
| PowerShell script blocked | Run with `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\<name>.ps1`. |

---

## 19. Release checklist

- [ ] `scripts/init-env.ps1` (or `.env` edited with unique secrets)
- [ ] `scripts/deploy-local.ps1` succeeds
- [ ] `docker compose ps` shows every service `healthy`
- [ ] `/health/ready/` and `/health/deep/` return `200`
- [ ] `scripts/smoke-test.ps1` passes
- [ ] Browser check of student and admin workflows
- [ ] `scripts/backup.ps1` creates and validates a backup
- [ ] `scripts/restore-drill.ps1` passes
- [ ] `scripts/secret-scan.ps1` is clean
- [ ] `scripts/rollback-rehearsal.ps1` passes
- [ ] `git status` contains only intended changes
- [ ] Do not push without explicit permission
