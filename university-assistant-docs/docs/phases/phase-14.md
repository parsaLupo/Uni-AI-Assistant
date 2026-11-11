# Phase 14 — Comprehensive Testing

## Objective
Harden the system through automated and scenario-based testing.

## Tasks
- backend unit/API/integration tests
- frontend tests
- end-to-end critical flows
- RAG golden dataset
- permission tests
- failure-mode tests

## Acceptance criteria
- [x] Critical user journeys pass.
- [x] Permission boundaries are tested.
- [x] RAG retrieval and grounding tests pass.
- [x] Migration/startup tests pass.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Execution record (Phase 14, 2026-11-11)

### 1. Permission matrix (backend, table-driven)

`backend/apps/common/tests/test_permission_matrix.py` — 112 table-driven rows
covering every path in the committed `backend/openapi.yaml` × four callers
(anonymous / STUDENT / PROFESSOR / ADMIN), plus an exhaustiveness test that
parses `openapi.yaml` and fails when a path is missing from the matrix.

Encoded boundaries (all are deliberate decisions, not accidents):

* academic reads require authentication — anonymous gets 401 (docs promise no
  anonymous access anywhere; the global DRF default is `IsAuthenticated`);
* `/auth/refresh/` and `/auth/logout/` without a cookie+CSRF pair return 403
  from the double-submit gate (ADR-014), for every caller;
* student-only surfaces (`/students/me/`, planner, course-selection) return
  403 to professor/admin because `_get_profile` raises `PermissionDenied` for
  non-students;
* `/admin/*` returns 401/403 for everyone except ADMIN/SUPERADMIN;
* owner-scoped conversation/planner detail routes return **404** (not 403) for
  foreign ids — the Phase 10 anti-enumeration decision.

### 2. Failure-mode tests (backend)

`backend/apps/common/tests/test_failure_modes.py` — 9 tests:

| failure provoked | documented outcome |
|---|---|
| expired access token | 401 `AUTHENTICATION_REQUIRED` envelope |
| Groq HTTP 429 categorization | `rate_limit`, retryable |
| rate-limited provider at ask time | 503 `AI_PROVIDER_ERROR`, Persian message, no "429" leak |
| database unreachable | `/health/` degrades to 503; driver text never in the body |
| concurrent planner add (unique race) | 409 `CONFLICT` from the DB backstop |
| duplicate student_number race | 409 `CONFLICT`, not 500 |
| malformed JSON body | 400 envelope, not 500 |
| empty `/ai/ask/` body | 400 `VALIDATION_ERROR` |
| failed document processing | status FAILED + retry re-enqueues (Celery `Retry` in eager mode) |

Provider outage/timeout/malformed-output and oversized/encrypted/malformed
uploads are covered by the existing suites (`apps/ai/tests/test_phase09.py`,
`apps/documents/tests/test_api.py`) and are referenced, not duplicated.

### 3. RAG golden dataset + automated runner

* `backend/apps/rag/golden_dataset.py` — expanded to **34 items** covering
  every docs/15 §3 category (regulations, prerequisites, exam schedule,
  academic calendar, professors, hybrid, unsupported) plus
  registration/scholarship/thesis, with docs/08 §4 fields
  (`expected_facts`, `forbidden`, `spell_variant`).
* `backend/apps/rag/golden_eval.py` — builds the docs/08 §4 sample corpus as
  real `Document`/`DocumentChunk` rows tagged `document_type="golden-sample"`
  (created and **removed inside every run**), evaluates retrieval + refusal,
  and writes `university-assistant-docs/reports/golden-set-report.{json,md}`.
  The corpus embeds with a 256-dimension hash projection: at the Phase 08
  64-dim setting, SHA-256 bucket collisions produced false positives above the
  retrieval threshold.
* `backend/apps/rag/management/commands/golden_run.py` — `manage.py golden_run`
  (development-only guard like `seed`, exit 1 on fail).
* Live run: **grounded 31/31 = 100 %** top-3 hit-rate (required ≥ 80 %);
  spell-variant equivalence ✅; the 3 unsupported items are refusal probes and
  their false-positive scores (0.21–0.40) are reported separately — the answer
  layer currently treats any non-empty retrieval as "sufficient" evidence, so
  tightening that margin is a Phase 15 hardening trigger.
* `backend/apps/rag/tests/test_golden_dataset.py` — 6 tests (structure,
  per-category coverage ≥ 3, unsupported ⇒ no source, automated full
  evaluation passes + corpus cleanup).

### 4. E2E — seven critical journeys (docs/08 §3)

* `frontend/playwright.config.ts` + `frontend/e2e/critical-journeys.spec.ts`
  (chromium, serial, baseURL `http://localhost:5173` against the Vite dev
  proxy → Docker backend).
* All **7 journeys pass** (58.7 s): registration → dashboard; courses → detail;
  professors → detail; exams with term context; assistant ask **with rendered
  document sources**; conversation follow-up + reload + history persistence;
  admin document upload → INDEXED → activate → ACTIVE (+ self-cleanup of the
  uploaded document).
* Determinism: `docker-compose.e2e.yml` forces `AI_PROVIDER=mock` for the
  backend so the assistant journeys never touch an external paid LLM.
* **Bug found and fixed by journey 5**: `apps/ai/answer.py` omitted
  `chunk_id` from `formatted_sources`, so the conversation layer silently
  dropped every `MessageSource` row and the UI showed no citations after
  asking (while `/ai/ask/` showed them). Fixed in both the sync and streaming
  paths; 106 AI/conversation tests re-run green.

### 5. Load / performance (docs/11)

* `backend/loadtest/load_probe.py` (stdlib-only threaded p95 probe) run
  against the seeded Docker backend on `GET /courses/`,
  `GET /course-offerings/`, `POST /ai/ask/` at 1 / 5 / 20 concurrent users;
  `backend/loadtest/k6_load.js` committed as the k6 equivalent (k6 and PyPI
  were unreachable on this machine).
* Recorded budget (docs/11 pins no number): non-AI reads **p95 ≤ 500 ms**,
  AI ask **p95 ≤ 2 000 ms**.
* Single-user: all routes within budget (worst p95 270 ms; RAG ask 122 ms).
  Concurrency: throughput saturates at ~10–14 rps (dev `runserver` + Docker
  Desktop port proxy), so u5/u20 breach the non-AI budget through queueing in
  the serving stack, not the application. Full numbers and the
  deployment-gate re-run (gunicorn) requirement:
  `university-assistant-docs/reports/load-test-report.md`.

### 6. CI

`.github/workflows/ci.yml`:

* backend job now runs `manage.py migrate --noinput` against the empty
  PostgreSQL service **before** pytest (migration-from-scratch gate);
* new `e2e` job: PostgreSQL service → migrate + seed → Playwright chromium →
  the seven journeys → artifact upload of the report.

### Full-suite verification

* Backend: `pytest` against `usa_test` (PostgreSQL + pgvector): **460 passed,
  0 failed** (334 before Phase 14; +126 new).
* Frontend: typecheck clean; vitest 65 passed (12 files) — unchanged.
* E2E: 7/7 journeys pass.

## Known limitations

1. Golden-set refusal behaviour is reported, not gated: unsupported questions
   still retrieve false positives (0.21–0.40) because the answer layer's
   `EvidenceSet.sufficient` is just "non-empty". Hardening the evidence margin
   is Phase 15 work (docs/15 §2 refusal/insufficiency).
2. Load numbers are for the development stack (`runserver` in Docker). The
   committed budgets must be re-measured on the gunicorn deployment
   (docs/09) before claiming concurrency capacity.
3. k6 itself could not be installed here (registry unreachable); the committed
   k6 script mirrors the stdlib probe and is the reproduction path.
4. The backend Docker image needed a rebuild during this phase (a bind-mounted
   code change added `pypdf`); because Docker Hub/PyPI were unreachable the
   package was copied from the host venv (6.21.2 vs pinned 5.3.1). `docker
   compose build backend` restores the pinned version once the registry is
   reachable.
5. CI's `e2e` job seeds via `manage.py seed`; it has not executed on a GitHub
   runner yet (next push will).
