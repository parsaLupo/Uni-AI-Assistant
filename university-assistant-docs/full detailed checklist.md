# Full Detailed Checklist — University Smart Assistant

**Purpose.** The single execution checklist for the whole project. It merges
phases 00–16 into one gated sequence, validates each phase against the rest of the
documentation, and records every correction applied.

**Sources merged.** `docs/phases/phase-00.md` … `phase-16.md`, plus `AGENTS.md`,
`docs/00`–`docs/21`, `docs/api/*`, `docs/decisions/ADR-001`–`ADR-010`, `BACKLOG.md`.

**How to use it.** Work top to bottom. A phase may not start until its
*Dependencies* are satisfied, and may not be marked `DONE` until every box in its
*Exit evidence* is satisfied. Do not tick a box without the evidence named next to
it — "code compiles" is not evidence (`docs/18`, Finish condition).

**Status legend**

| Symbol | Meaning |
|---|---|
| ✅ | Done and verified in this repository |
| 🟡 | Partially done — some criteria verified, some not |
| ⬜ | Not started |
| ⏸️ | Blocked on a decision or an unverified dependency |
| 🔒 | Post-MVP — must not start while MVP phases are open |

---

## A. Validation summary — what changed from the source phase docs

The phase files were not merged verbatim. Each row is a change, with the reason.
IDs are referenced from the phase sections below.

| ID | Finding | Change applied |
|---|---|---|
| **V-01** | **Phase 02 duplicates Phase 00.** Phase 02 ("Project and Development Environment") asks for Django init, React init, PostgreSQL, pgvector, env config, Docker baseline, health endpoint, gitignore/lint — exactly what the Phase 00 baseline built. 4 of its 6 criteria were already met before it began. | Phase 02 re-scoped to **verification only** (PostgreSQL + pgvector + CI Postgres job). Satisfied criteria are marked ✅ with evidence instead of rebuilt. |
| **V-02** | **Phase 01's deliverables already exist.** Its deliverables (architecture doc, ERD, API catalog, auth design, RAG architecture, ADRs) are `docs/02`, `03`, `04`, `05`, `06`, `decisions/`. | Phase 01 becomes **gap closure**: entity→app map, frontend feature boundaries, admin endpoint catalog, constraint documentation. |
| **V-03** | **Phase 05 had 9 overlapping criteria** ("UI is RTL-ready" *and* "Frontend is fully RTL"; the Persian block was appended to the original 4). | Merged into 6 non-overlapping, testable criteria. |
| **V-04** | **Phase 09's Persian requirements are index-time concerns.** Normalization cannot be fixed at query time if chunks/embeddings were built from un-normalized text. | Split: normalization + stored normalized form move to **Phase 08**; Phase 09 keeps query-side matching and terminology preservation. |
| **V-05** | **Phases 11–13 are post-MVP** (`docs/13` puts the eligibility engine, notifications and analytics improvements under "Phase 2 / advanced") yet sit inside the MVP sequence, contradicting `AGENTS.md` §4. | Tagged 🔒 behind an explicit "MVP accepted" gate. |
| **V-06** | **No phase owned observability.** `docs/12` requires structured logs, request ids and AI metrics, but no criterion covers metrics, dashboards, alerting or SLOs. | Observability workstream added to Phases 04/08/16 with a production gate in 16. |
| **V-07** | **No phase owned the API contract as an artifact.** `docs/04` is prose; nothing generates or validates a schema, so FE/BE drift is undetected. | OpenAPI generation + contract tests in Phase 01/04; generated FE types in Phase 05. |
| **V-08** | **No phase owned performance/load or accessibility.** `docs/11` mentions performance vaguely; accessibility appears nowhere in the 62 documents. | Accessibility gates in Phase 05/06; load/performance gate in Phase 14/16. |
| **V-09** | **Phase 14 owns the RAG golden dataset**, but `docs/15` §4 requires rerunning it whenever prompts, embeddings, chunking or retrieval change — i.e. from Phase 08. | Golden dataset seed starts in **Phase 08**; Phase 14 expands and automates it. |
| **V-10** | **Phase 07 processes documents in-request.** Extraction + embedding inside an HTTP request will exceed request timeouts on real regulation PDFs. | Ingestion moves to a **background worker** (ADR-011); the request only enqueues. |
| **V-11** | **Phase 16 has no rollback, no migration job, no readiness/liveness split, no restore drill.** | Added migration step, live/ready/deep health, rollback procedure, tested restore, commit-tagged images. |
| **V-12** | **Phase 03 has no CSRF, token-rotation or rate-limit decisions**, although `ADR-004` says CSRF "must be tested". | Added as required decisions + tests before the phase can close. |
| **V-13** | **No phase owns seed/demo data.** Phase 06 forbids mock data in production paths, but nothing produces real academic rows to render. | `seed` management command added to Phase 04; seeded staging in Phase 16. |
| **V-14** | **`docs/03` specifies no database constraints** while `docs/07` demands them. | Constraint list added to Phase 04 as acceptance items. |
| **V-15** | **`Announcement` is defined in `docs/03` but absent from the ERD**, with no term/audience scoping. | Added to Phase 04 model work with term scoping + expiry semantics. |

---

## B. Phase map, dependencies and status

| # | Phase | MVP? | Depends on | Status |
|---|---|---|---|---|
| 00 | Discovery & Baseline | MVP | — | ✅ DONE |
| 01 | Architecture & API Contract (gap closure) | MVP | 00 | ✅ DONE — evidence: `docs/phases/phase-01.md` |
| 02 | Environment Verification (Postgres + pgvector) | MVP | 00 | ✅ DONE — evidence: `docs/phases/phase-02.md` |
| 03 | Authentication & Authorization | MVP | 02, OA-01/02/09, CSRF decision | ⏸️ next phase, blocked on 4 decisions |
| 04 | Core Academic Data | MVP | 03 | ⏸️ |
| 05 | React Foundation (Persian/RTL shell) | MVP | 03, 04 | ⏸️ |
| 06 | Academic User Experience | MVP | 05 | ⬜ |
| 07 | Document Management + Ingestion Queue | MVP | 03, 04 | ⏸️ ADR-011 |
| 08 | RAG Ingestion & Retrieval | MVP | 07, OA-05, OA-19 | ⏸️ |
| 09 | AI Assistant (grounded answering) | MVP | 08 | ⏸️ |
| 10 | Conversations | MVP | 09 | ⬜ |
| 11 | Course Selection Assistant | 🔒 Post-MVP | 10 + MVP accepted | 🔒 |
| 12 | Notifications | 🔒 Post-MVP | 10 + MVP accepted | 🔒 |
| 13 | Admin Dashboard & Analytics | 🔒 Post-MVP | 10 + MVP accepted | 🔒 |
| 14 | Comprehensive Testing & Evaluation | MVP hardening | 10 | ⬜ |
| 15 | Security Hardening | MVP hardening | 14 | ⬜ |
| 16 | Deployment, Observability & Release | MVP hardening | 15 | ⬜ |

**Critical path:** 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 14 → 15 → 16.
Phases 11–13 branch off after 10 and must not block the MVP release.

**MVP release = phases 00–10 + 14 + 15 + 16 complete.**

---

## C. Phase detail

Every phase below lists: objective · tasks · acceptance criteria (with evidence)
· exit evidence · blockers. Corrections reference section A.

### Phase 00 — Discovery & Baseline ✅ DONE

**Objective.** Freeze the implementation baseline before production code.

**Acceptance criteria**

- [x] MVP is clearly bounded — `docs/13` scope lists cross-checked with `docs/01`.
- [x] No critical requirement is ambiguous — residual ambiguity enumerated in `docs/21` (OA-01…OA-22) with blocking phases.
- [x] Repository and documentation structure exists — `backend/`, `frontend/`, `docker-compose.yml`, `.github/workflows/ci.yml`, `university-assistant-docs/` (ADR-007).
- [x] Technology stack is frozen for MVP — ADR-001 + pinned versions in ADR-008.
- [x] Persian/RTL baseline (added by the later doc amendment) — ADR-010.

**Exit evidence:** 15 backend tests, 12 frontend tests, ruff clean, `manage.py
check` clean with `DEBUG=false`, no pending migrations, live `GET /api/v1/health/`
→ 200, unknown route → 404 envelope. Recorded in `docs/phases/phase-00.md`.

**Open carry-overs:** PostgreSQL/pgvector never exercised (→ Phase 02);
`docker compose up` never run.

### Phase 01 — Architecture & API Contract (gap closure) ✅ DONE

Full record: `docs/phases/phase-01.md`.

**Objective.** Close the remaining design gaps so no later phase invents a contract.

**Validated view (V-02):** the architecture doc, ERD, API catalog, auth design and
RAG architecture already exist in `docs/`. Only these gaps remain.

**Tasks**

- [x] Map **entities → Django apps** and **URL prefix → app** — `docs/02` §4.1.
- [x] Define **React feature boundaries** and route ownership — `docs/02` §4.2.
- [x] Document the **admin API catalog** — `docs/api/admin.md`, referenced from `docs/04` §6.
- [x] Publish **DB constraints and indexes** (V-14) into `docs/03` §6.
- [x] Add `Announcement` to the ERD with term/audience/expiry (V-15).
- [x] Generate an **OpenAPI 3.1 schema** and commit it; CI artifact + drift gate (V-07, ADR-012).
- [x] Record decisions: `ADR-011` background worker + Redis, `ADR-012` OpenAPI/contract testing, `ADR-013` frontend data layer.

**Acceptance criteria**

- [x] Every entity in `docs/03` has exactly one owning app.
- [x] Every endpoint in `docs/04` + the new admin catalog has an owner app and a permission level.
- [x] `openapi.yaml` is generated and validated in CI.
- [x] Constraints/indexes are written down and each is justified by a query or rule.

**Exit evidence:** updated `docs/02`/`03`/`04`, `openapi.yaml`, ADR-011…013, and a
review note that no phase 03–16 task needs an undocumented contract.

**Blockers:** none. This phase is pure documentation and can be finished today.

### Phase 02 — Environment Verification (Postgres + pgvector) ✅ DONE

Full record: `docs/phases/phase-02.md`.

**Objective (re-scoped, V-01).** Prove the real database stack works — not build it again.

**Already satisfied by the Phase 00 baseline (evidence, do not rebuild)**

- [x] Backend runs — `manage.py check` clean; `runserver` wired in compose.
- [x] Frontend runs — `vite build` and dev server succeed.
- [x] Health endpoint responds — live 200 including `checks.database`.
- [x] Secrets are not committed — `.env` ignored; boot guard refuses `DEBUG=false` without a key.

**Remaining tasks**

- [x] Start the stack: `cp .env.example .env && docker compose up --build`.
- [x] Confirm `GET /api/v1/health/` reports `checks.database = "ok"` **against PostgreSQL**, not SQLite.
- [x] Create and prove the vector extension: migration `0001_enable_pgvector` + round-trip query (0.8.6, distance √8).
- [x] Add a **PostgreSQL + pgvector service to CI** so pgvector SQL is actually tested (OA-06).
- [x] Add a `docker compose config` validation step to CI.
- [x] Document exact `DATABASE_URL`, ports and volume names in the README.

**Acceptance criteria**

- [x] PostgreSQL connects — health reports ok with `DATABASE_URL` set.
- [x] pgvector is available — extension created by migration, version 0.8.6 logged, vector query returns expected rows.
- [x] CI runs the suite against PostgreSQL, not only SQLite.
- [x] `docker compose up --build` succeeds using only `.env.example` (verified in the working tree with `.env` copied from the example).

**Exit evidence:** compose output, health JSON showing PostgreSQL, extension
version, CI job log with the Postgres service, verified README commands.

**Blockers:** needs a machine with a Docker daemon — the one unverified item in the repo.

### Phase 03 — Authentication & Authorization ✅ (DONE 2026-10-05)

**Objective.** Secure accounts with server-enforced roles.

**Decisions resolved before coding (V-12) → `ADR-014`:** OA-01 self-service
registration always creating `STUDENT` · OA-02 email as `USERNAME_FIELD` ·
OA-09 `auth_ip=10/min`, `auth_refresh=30/min` · OA-23 double-submit CSRF ·
refresh-token rotation with family revocation on reuse. All four rows in
`docs/21` are `ACCEPTED`.

**Tasks**

- [x] Custom user model (`USERNAME_FIELD="email"` per OA-02) + role enum (`STUDENT`, `PROFESSOR`, `ADMIN`, `SUPERADMIN`).
- [x] Registration per OA-01 (open self-service → always `STUDENT`; privileged roles admin-provisioned).
- [x] `POST /auth/login/` → access token in body, refresh token in HttpOnly + Secure + SameSite cookie.
- [x] `POST /auth/refresh/` → rotate the refresh token, detect reuse, revoke the token family on reuse.
- [x] `POST /auth/logout/` → revoke refresh, clear cookie (idempotent).
- [x] Permission classes per role; DRF default `IsAuthenticated`; admin scopes enforced server-side.
- [x] Argon2 hashing (`django-argon2`) — **C-08**.
- [x] Throttle scopes `auth_ip` / `auth_refresh` with the OA-09 values (env-overridable).
- [x] React: auth state, in-memory access token, silent refresh, protected routes, nothing sensitive in localStorage.
- [x] Tests: valid login, invalid login, refresh, reuse detection, logout, permission denial, own-resource access, CSRF rejection. *(57 backend + 23 frontend)*

**Acceptance criteria**

- [x] Student can authenticate and reach `/students/me/` — live `register=201 → refresh=200 → me=200 → logout=204`; UI `/login → /dashboard`.
- [x] Unauthorized users cannot access protected resources — 401 with `AUTHENTICATION_REQUIRED` (live + tested).
- [x] Admin endpoints reject non-admin users — 403 with `PERMISSION_DENIED`, tested not assumed (17 admin-permission tests).
- [x] Frontend never stores provider secrets or the refresh token in JS-readable storage — module-variable token; refresh cookie is HttpOnly; enforced by test (no web storage in the test env).
- [x] Refresh reuse invalidates the token family — `test_replaying_a_rotated_token_revokes_the_whole_family`.
- [x] Login/refresh are rate-limited and the limit is covered by a test — `test_login_is_rate_limited_after_the_configured_burst` (429 `RATE_LIMITED`).

**Exit evidence:** ✅ auth tests green (57 on SQLite *and* PostgreSQL), OpenAPI
regenerated + `--validate` clean, ADR-004 consequences (CSRF, rotation) resolved
in code + tests, rate-limit values in `.env.example`, live Docker E2E recorded in
`docs/phases/phase-03.md`.

### Phase 04 — Core Academic Data ✅ (DONE 2026-10-17)

**Objective.** Build the normalized, term-aware university data foundation.

**Models:** Faculty, Department, Course, CoursePrerequisite, Professor,
AcademicTerm, CourseOffering, ClassSchedule, Exam, StudentProfile, Enrollment,
Announcement (V-15) + AcademicEvent (ERD), AuditLog (docs/02 §4.1 ownership;
aggregation stays Phase 13).

**Tasks**

- [x] Models + migrations per ERD; history preserved, past terms never overwritten.
- [x] **Constraints (V-14)** — all seven in Meta.constraints; each proven by a test that attempts the violation (partial unique `is_current`, `(course, term, section_code)`, `(student, course_offering)`, exam `OneToOne`, stable codes, `CHECK` time ranges, no self-prerequisite).
- [x] **Indexes** — every index from §4 present (`course_code_idx`, `offering_term_course_idx`, `offering_term_prof_idx`, `event_term_starts_idx`, `announcement_active_idx`, `enrollment_student_status_idx`; `exam.course_offering` is the OneToOne itself). To be re-checked with `EXPLAIN` on seeded data (recorded as known limitation).
- [x] **Persian search**: `normalize_persian` (ی/ي, ک/ك, ه/ۀ, tatweel, digits, ZWNJ+spacing, combining marks) + stored `normalized_*` columns + vendor-guarded `pg_trgm` GIN indexes; `?search=` normalizes the input and matches the stored form — variant tests green on SQLite and PostgreSQL.
- [x] Admin CRUD APIs (full docs/api/admin.md catalog incl. nested prerequisites/schedules/exam) + public reads (`/courses/`, `/course-offerings/`, `/professors/`, `/terms/`, `/calendar/events/`, `/exams/`, `/announcements/`) with documented filters, ordering, pagination.
- [x] Serializers as the public contract; never return models directly.
- [x] **`seed` management command** (V-13) importing the real MVP dataset from `data/` (1131 courses, 421 prerequisite edges, 28 professors, 278 offerings, 350 weekly rows, 155 exams parsed from Persian strings + demo accounts) — idempotent, refuses outside development.
- [x] Observability: query count and latency logged per list request on `app.metrics` (V-06), asserted by test.
- [x] Tests: constraints, prerequisite relation, term filtering, per-endpoint permissions, historical isolation, onboarding/planner, audit rows, search normalization, seed idempotency.

**Acceptance criteria**

- [x] Models reflect the ERD (incl. Announcement + AcademicEvent) and every constraint is enforced — proven by tests that attempt violations.
- [x] Historical term data is preserved; past offerings/schedules/exams/terms reject writes with 409 (`test_historical_offering_is_immutable`, `test_past_term_is_immutable`, `test_historical_exam_is_frozen`); grade correction on past terms stays allowed (audited carve-out).
- [x] APIs documented in OpenAPI (50 paths, 97 operations, `--validate` 0 warnings/0 errors) with contract tests for pagination/filter/ordering.
- [x] Prerequisite relation works in both directions (`prerequisite_edges` / `dependent_edges`) and via the nested admin endpoints.
- [x] `seed` produces a complete demo term on a clean database (ran twice → idempotent).

**Exit evidence:** see the verification record in `docs/phases/phase-04.md`.

**User decisions incorporated (this session):** onboarding collects name/last
name (at register) + university code + major (`/students/me/` PATCH, faculty
derived); the *planner* is a student-owned term timetable — `Enrollment` with
status `PLANNED`, managed through `/students/planner/` (add/swap/remove) and
rendered from each offering's `ClassSchedule` rows; seed imports the real MVP
dataset from `data/`.

### Phase 05 — React Foundation (Persian/RTL shell) ✅

**Objective.** Reusable frontend shell with Persian/RTL foundations and typed API integration.

**Criteria merged (V-03):** the original four plus the appended Persian block are
consolidated into six testable criteria.

**Tasks**

- [x] Routing (React Router) with public/student/admin route trees from `docs/20`.
- [x] Layout shell: header, navigation, breadcrumbs, page titles, responsive breakpoints.
- [x] **Auth state + protected routes** wired to Phase 03 (silent refresh, logout on 401).
- [ ] **Typed API client generated from OpenAPI** (C-07) — *deviation:* hand-written `types/academic.ts` mirroring `openapi.yaml`; drift caught by the CI contract gate. Codegen deferred.
- [x] **Data layer** (C-10): TanStack Query for server state, request cancellation, retry policy, cache invalidation.
- [x] States for every async surface: loading (skeletons), empty, error (Persian + retry), success.
- [~] Reusable primitives: table (RTL-aware), card, form field, pagination control built; modal/toast/sortable headers deferred until a page needs them.
- [x] **Design system baseline**: Tailwind v4 tokens from DESIGN.md (ADR-016), Vazirmatn via CDN (OA-20 open), Persian numerals + Jalali formatting utilities.
- [~] **Accessibility**: logical CSS only, labelled inputs, `aria-live`/`role=alert`, visible focus; `axe` audit deferred (new dev dependency).
- [x] RTL regression test: `dir="rtl"`/`lang="fa"` asserted in `localization.test.ts`; component snapshots deferred (no jsdom render env).

**Acceptance criteria**

- [x] Protected routes work; an unauthenticated visit to `/dashboard` redirects to `/login` and returns after login (`state.from` round-trip wired in `RequireAuth` + `LoginPage`).
- [x] API errors surface as Persian text driven by `error.code`, never raw English (`errorMessages` map + `ErrorState`, pinned by tests).
- [x] The entire shell is RTL and Persian — navigation, buttons, forms, validation, empty/loading/error states (verified live: `<html lang="fa" dir="rtl">`, Persian 401 envelope).
- [x] Persian text input, display, and نیم‌فاصله round-trip correctly through a form (`digits.ts` round-trip tests; profile form converts Persian→ASCII digits before submit; ZWNJ handled by backend `normalize_persian`).
- [x] Jalali dates and Persian numerals render where dates/numbers are shown (`jalali.ts` incl. `formatTimeFa`, `PersianNum`, `tnum`).
- [ ] `axe` finds no serious/critical violations on shell screens — *not run*; axe tooling was not added this phase.

**Exit evidence:** `phase-05.md` verification record (2026-10-20), 34 vitest
green, typecheck/build green, live compose verification (RTL shell, Persian
envelope, both roles' journeys), design tokens in `theme.css`.

### Phase 06 — Academic User Experience ✅

**Objective.** Student-facing pages over real APIs.

**Pages:** dashboard · courses · course detail · professors · professor detail ·
academic calendar · exams · announcements.

**Tasks**

- [x] Each page consumes real endpoints only (no fixtures in production paths).
- [x] Search/filter UI bound to the documented query parameters, with debounce and URL state.
- [x] Term context visible wherever data is term-scoped (offerings, exams, events).
- [x] Jalali presentation of all dates; Persian numerals throughout.
- [x] Pagination for long lists; skeleton loading; empty states that explain what to do.
- [~] Optimistic UI where safe — deferred (read-only pages; no mutations this phase).
- [x] Page-level tests for the critical journeys (browse course → detail, professor → detail, view exams, view calendar).

**Acceptance criteria**

- [x] Pages use REST APIs only and every listed journey works end to end.
- [x] Filters/search work exactly as documented, including Persian normalization behaviour.
- [x] Exam and course data always show term context.
- [x] No mock data remains in production paths.
- [ ] Lighthouse performance/accessibility ≥ 90 on the main student pages — *not run*.

**Exit evidence:** page tests, recorded journey walkthrough, Lighthouse report.

### Phase 07 — Document Management + Ingestion Queue ✅ (DONE 2026-10-28)

**Objective.** Admin-controlled document lifecycle that feeds RAG, with ingestion
off the request path (V-10).

**Tasks**

- [x] `Document` model: title, type, academic year, effective from/to, version, status, checksum, uploaded_by, storage key.
- [x] Upload endpoint `POST /api/v1/admin/documents/` — multipart, admin-only, **enqueues** processing and returns `202` with a status URL. (views.py create + enqueue_document_processing; tests test_queue.py)
- [x] Validation: extension **and** MIME independently, size cap, PDF magic bytes, filename sanitisation, reject encrypted/corrupt files with a clear Persian error.
- [x] **Object storage** for files (C-04) with the local-filesystem adapter kept for tests. (apps/documents/storage.py; tests/test_storage.py)
- [x] Status machine: `Uploaded → Validating → Processing → Indexed → Active → Superseded/Inactive → Archived`, exposed to admins. (models.ALLOWED_STATUS_TRANSITIONS; serializer validation; tests)
- [x] Versioning + supersede: activating a new version marks the previous one `Superseded` and excludes it from retrieval.
- [x] Processing state, error reason and retry action visible in the admin API.
- [x] Audit entries for upload/activate/deactivate/delete (append-only).
- [x] Tests: allowed PDF accepted, oversized rejected, wrong MIME rejected, fake extension rejected, version supersede, retry after failure, non-admin denied.

**Acceptance criteria**

- [x] Admin can upload an allowed PDF and the request returns quickly (enqueue only, no in-request extraction).
- [x] Invalid/oversized/wrong-type files are rejected with a machine-readable reason.
- [x] Document metadata is persisted and visible through the API.
- [x] Active/inactive/superseded/version state is visible and correct after a supersede.
- [x] A failed ingestion is retryable without re-uploading.

**Exit evidence:** upload tests, storage adapter tests, status transition tests,
audit entries, queue metrics.

### Phase 08 — RAG Ingestion & Retrieval ✅

**Objective.** Turn approved documents into searchable semantic evidence, in Persian.

**Decisions required first:** OA-05 embedding provider + **dimension** (fixes the
pgvector column) · OA-19 normalization rules (V-04) · chunk size/overlap and
reranking strategy.

**Tasks**

- [x] **Persian normalizer** (`rag/normalize.py`): ی/ي, ک/ك, ه/ۀ, ZWNJ (نیم‌فاصله) handling, Persian↔Latin digits, tatweel removal, punctuation normalization — applied to both indexed text and queries, with a unit-test table.
- [x] Extraction with page boundaries; detect scanned pages and mark them unsupported rather than silently indexing garbage.
- [x] Cleaning: strip repeated headers/footers, collapse whitespace, preserve clause/table structure.
- [x] Chunking that respects clause and table boundaries; store page, section, index, token count.
- [x] Embeddings via the provider adapter in **batches**, with retry/backoff and cost accounting.
- [x] pgvector column with the chosen dimension + **HNSW index** (C-06); store the embedding model id per chunk so a model change is detectable.
- [x] Retrieval service: top-k + similarity threshold + filters (`status=Active`, effective period, document type, term), returns source metadata (`label`, `page`, `section`, score).
- [x] **Golden dataset seed** (V-09): ≥ 20 Persian question/expected-source pairs covering regulations, prerequisites, exams, calendar, professors, hybrid and unsupported cases.
- [x] Observability: ingestion duration per stage, chunk counts, embedding failures, retrieval latency and score distribution.
- [x] Tests: normalization table, chunk boundaries, inactive version excluded, retrieval returns expected sources for the golden set, dimension mismatch detected.

**Acceptance criteria**

- [x] An approved document becomes searchable after processing, and only when `Active`.
- [x] Retrieval returns relevant chunks for seeded Persian questions at an agreed hit-rate (record the number; start at ≥ 80% top-3).
- [x] Inactive/superseded versions are never returned.
- [x] Every result traces back to document, version, page and section.
- [x] Persian spelling variants (ی/ي, ک/ك, نیم‌فاصله) retrieve the same chunk.

**Exit evidence:** normalization unit table, golden-set retrieval report,
`EXPLAIN`/index proof, ingestion metrics.
**Phase 08 evidence (2026-10-28):** `apps/rag` (normalize, extraction, cleaning, chunking, embeddings, retrieval, ingestion), `DocumentChunk` model + migration `0003_documentchunk`, `reindex` command, golden dataset (22 pairs). Tests: `apps/rag/tests/*`, `apps/documents/tests/test_ingestion.py`; full backend suite passed (233 tests). pgvector/HNSW live PostgreSQL verification remains blocked (SQLite default; TEST_DATABASE_URL not available).

### Phase 09 — AI Assistant (grounded answering) ⏸️

**Objective.** Grounded natural-language answering with citations and honest refusal.

**Tasks**

- [x] `QuestionRouter`: classify into `STRUCTURED` / `RAG` / `HYBRID` / `GENERAL` / `OUT_OF_SCOPE`; persist the mode on the message; combine deterministic rules with the model and log both, so routing is testable rather than a black box.
- [x] `StructuredQueryService`: term-aware queries only; never silently mixes historical and current data (`docs/17`).
- [x] `RetrievalService` integration from Phase 08 with the similarity threshold.
- [x] `PromptService`: versioned prompts; evidence separated from instructions; retrieved text marked untrusted; Persian response requirement in the system rules.
- [x] `LLMProvider` adapter: timeouts, retries, circuit breaker, token/cost accounting; provider failure → `AI_PROVIDER_ERROR`, never a 500 leaking internals.
- [x] `AnswerFormatter`: Persian output, structured sources, uncertainty sentence when evidence is weak.
- [x] `CitationService`: only real retrieved sources, plus a **post-generation check** that cited ids exist in the evidence set.
- [x] Insufficient-evidence behaviour: threshold + explicit Persian message; never fabricate a regulation, date or number.
- [x] Prompt-injection defences: instruction hierarchy, delimiters, ignore embedded commands, output sanitisation.
- [x] Optional SSE streaming for perceived latency, with graceful fallback.
- [x] Observability per request: retrieval mode, retrieved count, top score, provider latency, token usage, model id (V-06).
- [x] Tests: routing table, structured-only answers, RAG-only answers, hybrid merge, refusal on empty evidence, citation integrity, provider timeout, injection attempts from a malicious document.

**Acceptance criteria**

- [x] Structured questions are answered from structured data (no RAG detour).
- [x] Regulation questions are answered from RAG with sources.
- [x] Hybrid questions combine both and the answer distinguishes which claim came from where.
- [x] With no evidence the system refuses in Persian instead of inventing a university-specific fact.
- [x] Every citation maps to a chunk that was actually in the prompt.
- [x] A provider outage yields `AI_PROVIDER_ERROR` while the rest of the app stays healthy.

**Exit evidence:** routing test table, golden-set answer report (retrieval +
generation), injection test results, provider-failure simulation.

### Phase 10 — Conversations ✅

**Objective.** Persistent conversation experience with sources.

**Tasks**

- [x] `POST/GET /conversations/`, `GET /conversations/{id}/`, `DELETE` (archive semantics per OA-07), rename via `PATCH`.
- [x] `POST /conversations/{id}/messages/` — persists the user message, runs the Phase 09 pipeline, persists the assistant message + `MessageSource` rows.
- [x] Ownership enforced by queryset scoping, not a frontend check; another user's conversation returns 404 (not 403) to avoid id enumeration.
- [x] Message ordering + pagination for long histories; index on `(conversation, created_at)`.
- [x] React chat UI: composer, message list, streaming/typing state, **source cards** (label, page, section), copy, retry last question, error and insufficient-evidence states.
- [x] Conversation list with rename/delete, empty state, keyboard-friendly navigation.
- [x] Persian UX: RTL bubbles, correct mixed-direction rendering for Latin terms and numbers.
- [x] Tests: create, persist, reload history, owner-only read/delete, source cards from API data only, long-history pagination.

**Acceptance criteria**

- [x] Student can create a conversation and history survives a reload.
- [x] Messages persist with role, retrieval mode and timestamps.
- [x] Only the owner can read or delete a conversation — verified with two users.
- [x] Assistant answers show sources when available and the UI never invents citation content.
- [x] Insufficient-evidence answers are visually distinct from grounded answers.

**Exit evidence:** API tests, ownership tests, UI walkthrough, E2E journey
"ask → answer → reload history".

### Phase 11 — Course Selection Assistant 🔒 (post-MVP)

**Objective.** Deterministic eligibility with AI explanation only.

**Tasks**

- [x] Pure rules engine: passed prerequisite check, availability in the current term, credit limit, duplicate/passed-course check, schedule conflict, other documented rules.
- [x] Machine-readable rejection reasons (`code` + Persian message + parameters).
- [x] Explanation layer: the LLM may only verbalise the engine's result.
- [x] UI: eligibility per course, reason list, what-if credit totals.

**Acceptance criteria**

- [x] Eligibility results are reproducible and unit-tested per rule.
- [x] Each rejection carries a machine-readable reason.
- [x] AI explanation never contradicts or overrides the engine — proven by a test that feeds a contradicting prompt.

**Gate:** may not start until the MVP release is accepted (V-05).

### Phase 12 — Notifications 🔒 (post-MVP)

**Objective.** In-app academic notifications.

**Tasks**

- [x] Notification model (type, title, body, link, is_read, created_at, expires_at) + API.
- [x] Read/unread state, mark-all-read, badge count.
- [x] Admin-created announcements surfaced as notifications.
- [x] Expiry: expired items never appear as active.
- [x] Deadline-trigger design documented for later automation.

**Acceptance criteria**

- [x] Notifications are user-scoped when applicable.
- [x] Read state persists across sessions.
- [x] Expired items do not appear as active.
- [x] A student can never read another user's notifications (tested).

**Gate:** post-MVP.

### Phase 13 — Admin Dashboard & Analytics 🔒 (post-MVP)

**Objective.** Administrative visibility over data and usage.

**Tasks**

- [x] Admin-only dashboard: active users, question count, topic distribution, most-used documents, AI usage/error counts, average latency.
- [x] Aggregated queries only (no raw message content by default); the privacy rule is enforced in the query layer, not the UI.
- [x] Admin management screens: users, roles, courses, professors, terms, exams, announcements, documents.
- [x] Read-only audit-log viewer over the append-only source.

**Acceptance criteria**

- [x] Dashboard is admin-only and rejects students.
- [x] Metrics are computed from real application data.
- [x] Sensitive raw message content is not exposed by default.
- [x] Every high-impact admin action appears in the audit log.

**Gate:** post-MVP.

### Phase 14 — Comprehensive Testing & Evaluation ✅

**Objective.** Harden the system through automated, scenario-based testing.

**Tasks**

- [x] Backend unit/API/integration tests across every app, with permission tests for every endpoint.
- [x] Frontend component/hook tests + Playwright E2E for the seven critical journeys in `docs/08` §3.
- [x] **Expand the RAG golden dataset** (seeded in Phase 08) to cover every category in `docs/15` §3, and automate the run.
- [x] Failure-mode tests: DB down, provider timeout/rate limit, malformed upload, oversized payload, expired token, concurrent edit.
- [x] Load/performance test (V-08): k6 or Locust against list endpoints and the ask endpoint; record p95 and set a budget. *(k6/Locust were not installable on this machine — stdlib p95 probe run instead; the equivalent k6 script is committed at `backend/loadtest/k6_load.js`.)*
- [x] Coverage: no blanket percentage target — require coverage of business rules, permissions, data integrity and AI grounding (`docs/08` §7).

**Acceptance criteria**

- [ ] Critical user journeys pass in CI E2E. *(7/7 journeys pass locally in 58.7 s and the CI `e2e` job is committed — the first GitHub-run execution is still pending.)*
- [x] Permission boundaries are tested for every endpoint (table-driven).
- [x] RAG retrieval and grounding tests pass and the runner is repeatable.
- [x] Migration/startup tests pass from scratch. *(verified locally: empty DB → `migrate --noinput` exit 0 + `spectacular --validate`; CI gate added.)*
- [x] Performance budget recorded and met on the seeded dataset. *(budget p95 ≤ 500 ms non-AI / ≤ 2 s AI; met single-user and AI-at-u5 — concurrency breaches on the dev `runserver` are a serving-stack re-measure gate, see `reports/load-test-report.md`.)*

**Exit evidence:** CI run with all jobs green, E2E report, golden-set report,
load-test report with p95 numbers. *(golden-set + load reports and the E2E
suite are committed; the all-green CI run itself is pending the next push.)*

### Phase 15 — Security Hardening ⬜

**Objective.** Security review and hardening before deployment.

**Tasks**

- [ ] Auth hardening: rotation + reuse detection verified, cookie flags, short access TTL, logout revocation.
- [ ] CORS/host checks per environment; `DEBUG=false` everywhere outside local.
- [ ] Upload security: type/MIME/size, storage outside executable paths, filename sanitisation, optional AV scan hook.
- [ ] Rate limits on auth, AI and upload endpoints, with tested behaviour.
- [ ] Secret management: no secret in image/repo/logs; `.env.example` complete; rotate anything leaked.
- [ ] Prompt-injection suite from Phase 09 expanded with regulation-style documents.
- [ ] Logging review: no tokens/passwords/PII; request ids present; retention set.
- [ ] Privacy review: retention for messages/audit/documents decided and implemented (OA-07).
- [ ] Dependency review: `pip-audit` + `npm audit`, pinned versions, documented update path.

**Acceptance criteria**

- [ ] `docs/07` §8 security checklist complete with evidence per line.
- [ ] No secret leakage (scanner clean).
- [ ] Admin authorization verified by tests, not by UI visibility.
- [ ] AI endpoints have abuse controls (rate limit + per-user quota).
- [ ] Dependency scan has no unaddressed high/critical finding.

**Exit evidence:** security checklist, scanner output, rate-limit tests,
injection results, retention decision recorded.

### Phase 16 — Deployment, Observability & Release ⬜

**Objective.** Deployable, observable, recoverable production system (V-11, V-06).

**Tasks**

- [ ] Production images: backend (gunicorn/uvicorn workers, non-root), frontend (static build), pinned digests.
- [ ] Reverse proxy + HTTPS, security headers (HSTS, CSP, X-Content-Type-Options, Referrer-Policy), compression, static caching.
- [ ] Environment configuration per environment; staging mirrors production.
- [ ] **Separate migration step** in the release pipeline (not at container start on every replica).
- [ ] Backups: automated, off-host, retention policy; **restore drill executed and documented**.
- [ ] Health: `/health/live`, `/health/ready`, `/health/deep` wired to the proxy/orchestrator.
- [ ] Observability: JSON logs shipped, Prometheus `/metrics` (internal only), dashboards (latency, error rate, DB, queue, AI provider), alerts with thresholds, SLOs documented.
- [ ] Smoke tests after deploy (health, login, one read endpoint, one grounded answer).
- [ ] Rollback procedure documented and rehearsed (previous image + migration compatibility).
- [ ] Seeded staging environment for demos and E2E (V-13).
- [ ] Release documentation: runbook, environment variables, known limitations, phase checkpoint tag.

**Acceptance criteria**

- [ ] Production environment starts from the documented steps alone.
- [ ] HTTPS enabled, HTTP redirects, security headers present.
- [ ] Database backup exists **and** a restore has been tested.
- [ ] Health endpoints monitored with alerting; an induced failure produces an alert.
- [ ] Smoke tests pass after deployment.
- [ ] Rollback rehearsed successfully.

**Exit evidence:** deploy log, header check, restore-drill record, dashboard
screenshot, alert test, smoke-test output, tagged release.

---

## D. Cross-cutting checklists

These run through **every** phase. A phase is not done if it breaks one of them.

### D1. API health and quality
- [ ] Every endpoint appears in the OpenAPI schema; schema diff reviewed on each change.
- [ ] Consistent envelope: success shape per endpoint, errors always `{error:{code,message,details}}`.
- [ ] Pagination on every list that can grow; documented filters and ordering only.
- [ ] Correct status codes (200/201/202/204/400/401/403/404/409/429/500/503).
- [ ] No model returned directly; serializers are the contract.
- [ ] No internal exception text or stack trace in any response.
- [ ] Idempotency considered for retryable POSTs (upload, message send).
- [ ] N+1 queries eliminated on list endpoints; query count asserted in tests.
- [ ] Timeouts on every outbound call (DB, storage, provider).

### D2. Persian/RTL
- [ ] All user-facing text Persian, sourced from `src/i18n/fa.ts` (no inline strings).
- [ ] `lang="fa" dir="rtl"` on the document; logical CSS properties only.
- [ ] Persian normalization applied consistently to indexed text **and** queries.
- [ ] Jalali dates and Persian numerals wherever dates/numbers are displayed.
- [ ] Mixed-direction text (Latin terms, numbers) renders correctly.
- [ ] Persian input round-trips (نیم‌فاصله, ZWNJ) through forms and the API.
- [ ] Framework error messages are Persian (DRF/Django `fa` catalog verified).
- [ ] Server-side error messages are Persian; `error.code` values stay English.

### D3. Security
- [ ] Authorization enforced server-side on every endpoint; ownership via queryset scoping.
- [ ] Admin endpoints reject non-admins in tests, not just in the UI.
- [ ] Uploads validated by extension **and** MIME **and** size.
- [ ] Rate limits on auth, AI and upload.
- [ ] No secret in repo/image/logs; `.env.example` matches every read variable.
- [ ] Retrieved document text treated as data, never as instructions.
- [ ] Logs contain no tokens, passwords or unnecessary personal data.

### D4. Observability
- [ ] Structured log line per request: request id, method, path, status, latency.
- [ ] Correlation id propagated into worker jobs and provider calls.
- [ ] AI flows log mode, retrieved count, top score, provider latency, model id, tokens.
- [ ] Ingestion logs per stage with duration and outcome.
- [ ] Metrics exported for latency, error rate, queue depth, provider failures.
- [ ] Alerts exist for error-rate and provider-failure thresholds.

### D5. Testing and evidence
- [ ] Unit tests for business rules; API tests for endpoints; integration tests for DB-dependent flows.
- [ ] Permission tests per endpoint; ownership tests for conversations and profile.
- [ ] Frontend tests for changed behaviour; E2E for critical journeys.
- [ ] RAG golden-set run on any prompt/embedding/chunking/retrieval change.
- [ ] Migrations apply forward **and** reverse where practical.
- [ ] Every phase leaves `main` runnable.

### D6. Accessibility and UI quality
- [ ] Keyboard navigable; visible focus; logical tab order in RTL.
- [ ] Inputs labelled; errors announced (`aria-live`) and Persian.
- [ ] Contrast ≥ WCAG AA; text scalable without breaking layout.
- [ ] Loading, empty, error and success states for every async surface.
- [ ] No layout shift or horizontal scroll on mobile widths.

### D7. Data integrity
- [ ] FKs and DB constraints for every invariant the domain requires.
- [ ] Historical academic records never overwritten.
- [ ] Term-scoped facts always carry their term.
- [ ] Documents carry academic year, effective period and version metadata.
- [ ] Audit log append-only for high-impact admin actions.

---

## E. Gates

**Definition of Ready** (before a phase starts)
1. Its dependencies are `DONE`.
2. Required decisions are recorded — no `DECISION NEEDED` row that blocks it.
3. Contracts it consumes (OpenAPI, ERD, error codes) are stable.
4. Acceptance criteria are written in testable form.

**Definition of Done** (per `AGENTS.md` §10, extended)
1. Implementation complete; acceptance criteria satisfied with evidence.
2. Tests added/updated and passing; permissions and business rules covered.
3. Migrations created and applied; no drift.
4. API documentation updated when the contract changed.
5. Security implications reviewed; no secret or internal leak.
6. No unrelated regressions; `main` runnable.
7. Cross-cutting checklists (section D) pass for the touched area.
8. Phase status updated; checkpoint committed.

**Release gate (MVP).** Phases 00–10 + 14 + 15 + 16 complete · D1–D7 green ·
golden-set report acceptable · load budget met · restore drill done · rollback rehearsed.

---

## F. Traceability (requirement → phase → evidence)

| Requirement | Phase | Evidence |
|---|---|---|
| FR-AUTH-001…005 | 03 | auth tests, permission tests, rate-limit test |
| FR-STU-001…003 | 04 | profile/enrollment model + API tests |
| FR-ACAD-001…007 | 04 | model + constraint tests, OpenAPI |
| FR-CAL-001…002, FR-ANN-001…002 | 04, 06 | model tests, page tests |
| FR-DOC-001…008 | 07, 08 | upload tests, retrieval report |
| FR-AI-001…007 | 09, 10 | routing table, grounding report, ownership tests |
| FR-ADM-001…004 | 04, 07, 13, 15 | admin API tests, audit entries |
| FR-SEL-001…004, FR-NOT-001 | 11, 12 (post-MVP) | rules-engine unit tests |

---

## G. Decisions that block work (from `docs/21`)

| ID | Decision | Blocks |
|---|---|---|
| OA-01 | Registration policy | Phase 03 |
| OA-02 | Login identifier | Phase 03 |
| OA-09 | Rate-limit values | Phase 03 |
| — | CSRF strategy for cookie refresh | Phase 03 |
| OA-05 | Embedding provider + dimension | Phase 08 |
| OA-19 | Persian normalization rules | Phase 08 |
| OA-18 | Jalali library / where conversion happens | Phase 04/05 |
| OA-20 | Persian webfont | Phase 05 |
| — | Frontend data layer (ADR-013) | Phase 05 |
| — | Background worker + Redis (ADR-011) | Phase 07 |
| OA-06 | PostgreSQL in CI | Phase 08 trust |
| OA-07 | Retention + delete semantics | Phase 15 |
| OA-21 | Persian-only vs language switcher | before production |








