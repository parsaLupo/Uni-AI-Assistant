# Phase 15 — Security Hardening

## Objective
Perform security review and hardening before deployment.

## Tasks
- auth hardening
- CORS/host checks
- upload security
- rate limits
- secret management
- prompt injection tests
- logging review
- privacy review
- dependency/update review

## Acceptance criteria
- [x] Security checklist complete.
- [x] No obvious secret leakage.
- [x] Admin authorization verified.
- [x] AI endpoints have abuse controls.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

---

## Execution record (Phase 15 — done)

### What the audit found already in place

Auth rotation + reuse detection (ADR-014), refresh cookie `HttpOnly`/`Secure`/`SameSite=Lax` scoped to the auth path, 5-min access / 7-day refresh TTL, Argon2id, logout revocation, per-IP + per-user auth throttles, CORS/hosts explicit per env, DEBUG=false default with secret refusal outside dev, upload validation (10 MB, `.pdf`, MIME allowlist, `%PDF` magic, `/Encrypt` rejection, filename sanitisation, checksum-derived storage key under `DOCUMENT_STORAGE_ROOT`), access logs carrying request id/method/path/status/latency only, and an admin permission matrix of 112 endpoint×role rows.

### Changes made

**Transport hardening** (`config/settings.py`)
- `SECURE_SSL_REDIRECT` (on outside dev/tests, overridable), `SECURE_HSTS_SECONDS` (1 y when not DEBUG, subdomains+preload), `SECURE_PROXY_SSL_HEADER` (trust `X-Forwarded-Proto` at the TLS-terminating proxy), `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY=same-origin`, `X_FRAME_OPTIONS=DENY`.

**Rate limits** (`apps/common/throttles.py` — new)
- `AiAskRateThrottle` (`ai_ask`, default `20/min`) on `/ai/ask/` **and** `/ai/ask/stream/` — one shared per-user budget, checked in DRF `initial()` before the provider is called.
- `UploadRateThrottle` (`upload`, default `10/min`) on admin document `create`/`retry` (both enqueue ingestion); reads/metadata updates unthrottled.
- Keyed by verified user id, IP fallback. 429s use the existing documented `RATE_LIMITED` envelope with `retry_after_seconds` (`apps/common/errors.py` — no change needed).

**Privacy / retention (OA-07 closed)** (`apps/conversations/management/commands/apply_retention.py` — new)
- Policy decided and implemented: archived conversations **hard-deleted** `RETENTION_CONVERSATION_DAYS` (default 180) days after `archived_at`; messages + message sources cascade; documents retained as official records; audit/telemetry append-only. Command is cron-safe, refuses to delete without `--yes`, supports `--dry-run`.

**Prompt-injection suite expanded** (`apps/ai/tests/test_injection_hardening.py` — new)
- Full-pipeline tests against regulation-style documents whose chunks carry English + Persian injection payloads: prompt keeps a single `SYSTEM RULES` header and wraps every retrieved chunk in `UNTRUSTED DATA`; `sources` describe only real DB chunks; planted `[7]`/`[999]` citations are stripped; injection-only questions route `OUT_OF_SCOPE` and are refused; university-flavoured overrides stay RAG + grounded.

**Logging review** (`apps/common/tests/test_logging_hygiene.py` — new)
- Proves access logs contain no password / refresh token / question text / query string, and every access record carries a non-trivial correlation id.

**Production settings boot** (`apps/common/tests/test_production_settings.py` — new)
- Real subprocess with `DJANGO_DEBUG=false` asserts the hardening flags, secure cookies, empty CORS without explicit origins, explicit `ALLOWED_HOSTS`, and that boot refuses without `DJANGO_SECRET_KEY`.

**Secret management**
- `.env.example` completed: `RATE_AI_ASK`, `RATE_UPLOAD`, `RETENTION_CONVERSATION_DAYS`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `CELERY_*`, `DOCUMENT_STORAGE_ROOT`.
- New CI `secret-scan` job greps tracked files for `gsk_*`/`sk-*`/`AKIA*`/`BEGIN … PRIVATE KEY`; local run clean.

**Dependency review**
- `pip-audit` (now installed and reproducible): found DRF 3.18.1 (3 CVEs), pypdf (15 CVEs across 5.3.1 and 6.21.2), pip tooling PYSECs. **All fixed:** `djangorestframework==3.18.2`, `pypdf==6.21.4`, pip upgraded to 26.3 — audit of environment *and* committed pins is clean.
- `npm audit`: vite 8.3.1 high-severity GHSA set → `vite@8.3.8` exact; `npm audit` now reports 0 vulnerabilities; typecheck + 65 vitest tests pass.
- Update path documented in `docs/07-security.md` §8 (bump pin → run suite + audit → record reason in pin comment).
- No new dependency added (AGENTS rule 10); `pip-audit` is a dev tool only.

**Incidental fix found by the lint pass**
- `apps/courses/views.py` contained **double-encoded (mojibake) Persian** in all of its user-facing error strings (a PowerShell-write artefact from an earlier phase). Recovered the proper Persian by reverse round-tripping; no test asserted the corrupted text; courses/professors suites pass.
- Pre-existing ruff violations in 16 tracked files cleaned (~90 errors: import order, line length, unused locals) so CI's `ruff check .` can go green; only untracked scratch files still carry lint errors.

### Tests run
- Full backend suite against PostgreSQL + pgvector: **483 passed, 12 subtests** (23 new tests this phase: 7 throttle, 3 production-settings, 3 logging-hygiene, 5 injection-hardening, 5 retention).
- `ruff check apps config`: clean. `manage.py spectacular --validate`: valid, no contract drift. `manage.py golden_run`: golden set PASS (grounded 100%, unsupported 0/3). Frontend: `tsc --noEmit` clean, 65 vitest tests passed, `npm audit` clean.

### Migrations
- None (no model changes).

### Acceptance criteria status
- Security checklist complete: `docs/07-security.md` §8 — every line ticked with evidence.
- No obvious secret leakage: CI secret-scan job + local grep clean; dev key refused outside DEBUG/tests.
- Admin authorization verified by tests: permission matrix (112 rows) + openapi exhaustiveness.
- AI endpoints have abuse controls: per-user `ai_ask` throttle on ask + stream, per-admin `upload` throttle, 429 envelope tested.

### Known limitations
- `pip-audit` / `npm audit` run locally, not yet as CI jobs (network-gated CI step to add in Phase 16 alongside the scheduled scan).
- The Docker backend image still pins the old `pypdf==5.3.1` in its layer — `docker-compose` image rebuild required (registry was unreachable this session); the requirements pin is now 6.21.4.
- AV scanning is a documented hook point, not wired (no scanner in the MVP deployment).
- HSTS/HTTPS redirect default ON only outside dev/tests; the reverse-proxy TLS wiring itself is Phase 16.
