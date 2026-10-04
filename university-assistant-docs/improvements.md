# Improvements — University Smart Assistant

Review of the 62-document specification and the existing baseline, written from the
position of "what will actually hurt when this is in production". Every item states
the problem, the evidence, the recommended change, and the signal that proves it is
fixed.

**Priority**

- **P0** — blocks a phase, or causes data/security/rework damage if ignored.
- **P1** — design gap that will force rework in a later phase.
- **P2** — hygiene, quality, developer experience.

**Effort:** S (hours) · M (days) · L (a week+).

---

## P0 — do before the next phase starts

### I-01 · Verify PostgreSQL + pgvector (S)
**Problem.** Nothing in this repository has ever touched real PostgreSQL. Tests run on
SQLite and `docker compose up` has never been executed, so Phase 02's criteria
"PostgreSQL connects" and "pgvector is available" are unverified — and every later
phase assumes them.
**Change.** Run the stack, create the extension, prove a vector round-trip, add a
PostgreSQL + pgvector service to CI.
**Signal.** Health reports `database: ok` against PostgreSQL; CI runs on Postgres;
extension version logged.

### I-02 · Resolve the Phase 00 / Phase 02 overlap (S)
**Problem.** Phase 02 asks for what the baseline already built (Django init, React
init, Postgres, pgvector, env config, Docker, health endpoint, lint baseline). Left
as-is, an agent either rebuilds working code or marks the phase done twice.
**Change.** Phase 02 becomes verification-only (`full detailed checklist.md` V-01).
**Signal.** Phase 02 closes with evidence, not new files.

### I-03 · Decide the four Phase 03 blockers (S)
**Problem.** Registration policy, login identifier, rate-limit values and the CSRF
strategy for cookie-based refresh are undecided, yet Phase 03 cannot be implemented
correctly without them — and the user model is the most expensive thing to change later.
**Evidence.** OA-01, OA-02, OA-09, ADR-004 ("CSRF considerations must be tested").
**Change.** Record all four in `docs/21` + an ADR before Phase 03 starts.
**Signal.** No `DECISION NEEDED` row blocking Phase 03 remains.

### I-04 · Close the admin API catalog gap (S)
**Problem.** Phase 04 requires admin CRUD for courses, professors, terms, exams and
announcements, but `docs/04` §6 documents only `/admin/documents/` and
`/admin/analytics/summary/`. Implementing undocumented endpoints breaks `AGENTS.md` §6.
**Change.** Add an admin endpoint catalog with permissions, filters, idempotency notes.
**Signal.** Every Phase 04 endpoint exists in the catalog before it exists in code.

### I-05 · Fix the embedding model and dimension before ingestion (M)
**Problem.** The pgvector column dimension must be fixed before the first migration;
changing the model later means re-embedding the whole corpus. `docs/03` leaves the type
open and `docs/06` defers indexing until "after measuring".
**Change.** Decide provider + model + dimension (OA-05), assert the dimension at
startup, store `embedding_model`/`embedding_dim` per chunk, use HNSW.
**Signal.** A dimension mismatch fails fast instead of silently degrading retrieval.

### I-06 · Move Persian normalization into ingestion (M)
**Problem.** `docs/11` and Phase 09 list Persian variants (ی/ي, ک/ك, نیم‌فاصله, digits)
as retrieval requirements, but if chunks were embedded from un-normalized text no
query-side fix can recover recall — the requirement is owned by the wrong phase.
**Change.** Implement `normalize_persian` in Phase 08, apply it to indexed text **and**
queries, store normalized columns, index them with `pg_trgm`.
**Signal.** A search for «دانشكاه» (Arabic kaf) finds «دانشگاه»; variant-spelling golden
queries retrieve the same chunk.

### I-07 · Make API contracts machine-checkable (M)
**Problem.** `docs/04` is prose, so frontend/backend drift is invisible, and the
frontend hand-maintains its own types.
**Change.** Adopt `drf-spectacular`, commit `openapi.yaml`, fail CI on unreviewed
schema changes, generate the frontend client/types.
**Signal.** A renamed or removed field fails CI before merge.

### I-08 · Fix conversation retention and delete semantics before Phase 10 (S)
**Problem.** `docs/14` requires a retention policy before production but leaves
hard-delete vs soft-delete vs archive undecided (OA-07). Conversation rows carry
personal questions and retrieved excerpts; retrofitting deletion onto a populated
table is where data-exposure incidents live.
**Change.** Decide: soft-delete + scheduled purge (recommended) with `deleted_at`,
cascade rules for `Message`/`MessageSource`, and a documented export path.
**Signal.** A delete request disappears from every query path within the agreed
window, and the purge job has a test.

---

## P1 — design gaps that force rework if deferred

### I-09 · Document database constraints in `docs/03` (S)
**Problem.** `docs/07` demands database integrity constraints, but the ERD specifies
none: unique (offering, section, term), unique (student, offering) for enrollment,
"at most one current term", "one exam per offering". Without them, duplicates are
prevented only by application code — which every future endpoint must remember.
**Change.** Add UNIQUE/CHECK/FK constraints to `docs/03`, implement them in the
Phase 04 migrations, and test with constraint-violation tests, not just happy paths.
**Signal.** A second identical enrollment insert fails at the database, proven by a test.

### I-10 · Put `Announcement` in the ERD and define `Notification` semantics (S)
**Problem.** `Announcement` is defined as an entity but missing from the ERD, with
no term scoping, audience or expiry; `Notification` has no type or expiry either —
yet Phase 06/12 criteria depend on "expired items hidden".
**Change.** Add both to the ERD with `term?`, `audience`, `published_at`,
`expires_at`, `status`; decide hard-filter vs scheduled job for expiry.
**Signal.** An expired announcement disappears from list and detail endpoints, tested.

### I-11 · Fix the Jalali date contract (OA-18) before Phase 04 (S)
**Problem.** Jalali conversion decided per screen is how date bugs are born: the API
and the UI must agree once. Currently undecided, blocking Phases 04 and 05.
**Change.** Contract: API always returns UTC ISO-8601; the frontend renders Jalali
via one adapter module (e.g. `jalaali-js`/`date-fns-jalali`); record it in `docs/21`.
**Signal.** One formatter function; a test asserts 2026-03-21T00:00:00Z renders as
۱ فروردین ۱۴۰۵.

### I-12 · Choose the frontend data layer before Phase 06 (S)
**Problem.** Ten-plus pages of server state with hand-rolled `fetch` means every
page reinvents caching, loading states, retries and invalidation — the top source of
frontend bugs in CRUD apps. AGENTS rule 10 forbids an undocumented dependency, so
this must be decided, not improvised.
**Change.** ADR-013: TanStack Query (recommended) + typed endpoints generated from
OpenAPI; document it in `docs/02`.
**Signal.** No page contains manual `useEffect` fetch/abort boilerplate.

### I-13 · Plan seed/demo data (V-13) (M)
**Problem.** Phase 06 forbids mock data in production paths, but nothing produces
real academic rows to render; without it UI work stalls or devs hardcode fixtures.
**Change.** `manage.py seed` — deterministic, idempotent — producing faculties,
terms, courses, prerequisites, offerings, schedules, exams, announcements; guarded
to non-production settings; optionally loads a small Persian PDF corpus.
**Signal.** Fresh clone → migrate → seed → login shows a fully populated UI.

### I-14 · Start the golden dataset in Phase 08, automate in Phase 14 (S)
**Problem.** `docs/15` §4 requires rerunning evaluation whenever prompts, models,
chunking or retrieval change — i.e. from the first ingestion release — but the
dataset is assigned to Phase 14, so early changes ship unevaluated.
**Change.** Seed the Persian golden set (question → expected source/page/facts,
including negative/refusal cases) in Phase 08 and run it as a CI job; Phase 14
expands coverage and enforces thresholds.
**Signal.** Changing the prompt template fails CI when recall drops.

### I-15 · Make accessibility a phase criterion (M)
**Problem.** Accessibility appears in none of the 62 documents. Persian RTL forms,
keyboard navigation and screen-reader labels are cheap to build and very expensive
to retrofit after Phase 06.
**Change.** Add to Phases 05/06: semantic landmarks, labelled inputs, focus-visible,
contrast ≥ 4.5:1, keyboard-operable modals/tables, RTL-correct focus order.
**Signal.** An automated axe run in CI plus a manual keyboard pass per page.

### I-16 · Decide the observability stack, not just the log format (M)
**Problem.** `docs/12` specifies log *fields* but no stack, no metrics surface, no
alerting and no SLOs — and Phase 13's "latency and error metrics" criterion has
nothing to measure against.
**Change.** Before Phase 16: structured JSON logs → collector; error tracking
(Sentry-compatible, self-hostable); Prometheus-style `/metrics` or APM; define 3–4
SLOs (p95 latency, error rate, answer availability, ingestion success) with alerts.
**Signal.** A deliberate error appears in the dashboard with its request id within
minutes, and an alert fires on SLO burn.

### I-17 · Design rate limiting and AI abuse controls concretely (S)
**Problem.** OA-09 leaves limits undecided while Phases 03/15 both assume them;
unlimited `/ask` calls are a cost and availability incident, not just a security note.
**Change.** Tiered limits (anonymous / authenticated / admin), per-IP and per-user
buckets in Redis, quotas on conversation and question length, circuit breaker on
provider errors — with numbers documented in `docs/21`.
**Signal.** A burst test gets 429 with `RATE_LIMITED`, not a provider bill.

### I-18 · Put uploads behind an object-storage abstraction (M)
**Problem.** Local-disk uploads break with more than one backend replica and
complicate backup (ADR-014). Phase 07 builds the upload path — deciding afterwards
means migrating stored files.
**Change.** ADR-014: S3-compatible storage with a local-filesystem adapter for dev;
SHA-256 checksum stored on `Document`.
**Signal.** Dev uses a folder, staging uses a bucket, same code path.

### I-19 · Close the error-taxonomy seam (S)
**Problem.** Health's 503 reports `INTERNAL_ERROR`, so a transient outage is
indistinguishable from a bug; ADR-009's extensions live outside `docs/12`, so that
spec page is no longer self-contained.
**Change.** Add `SERVICE_UNAVAILABLE`; fold ADR-009 back into `docs/12` (keep the
ADR as the decision record); codes stay English, messages Persian (ADR-010).
**Signal.** `docs/12` lists every code the codebase can emit; a test enumerates them.

---

## P2 — hygiene, quality, developer experience

### I-20 · Pre-commit hooks (S)
ruff + `manage.py check` + `tsc --noEmit` via pre-commit — enforced before CI sees it.
**Signal:** a deliberately broken commit is blocked locally.

### I-21 · Pin runtimes explicitly (S)
`.python-version` (3.13), `.nvmrc`/`engines` (Node 22); AGENTS forbids unapproved
version drift, pins make the approval mechanical.
**Signal:** wrong version → install tooling refuses with a clear message.

### I-22 · Validate compose in CI (S)
`docker compose config` plus a Postgres+pgvector service job (extends I-01). Compose
has never been executed or parsed by any check.
**Signal:** malformed YAML or a bad env reference fails the PR.

### I-23 · Extend the docs reading order (`docs/README.md`) (S)
The agent reading order stops at `06` and omits `21-open-assumptions.md`, the ADR
index and the four summary docs.
**Signal:** a new agent finds the blocking decisions in two clicks.

### I-24 · Map BACKLOG EPICs to phases (S)
EPIC 11 = phases 14/15; EPICs 9/10 = post-MVP 11/12. Ambiguity here is how an agent
starts building post-MVP features mid-MVP, violating AGENTS §4.
**Signal:** every backlog item names its phase.

### I-25 · Register the four summary docs (S)
`full detailed checklist.md`, `architecture.md`, `pipeline.md`, `improvements.md`
must appear in `FILE-INVENTORY.md` and `docs/README.md`, and `START-HERE.md` should
point at the checklist as the execution view.
**Signal:** inventory count matches reality (it was wrong once already).

### I-26 · Dependabot/Renovate + lockfile hygiene (S)
Automated PRs for pip/npm/base images — review *is* the approval AGENTS requires.
**Signal:** weekly update PRs with green CI.

### I-27 · Formatting normalization (S)
Prettier for frontend/docs, trailing-newline enforcement (several amended docs lack
one). **Signal:** `prettier --check` in CI.

### I-28 · UI quality baseline before Phase 05 (M)
Design tokens (spacing/color/typography for Persian RTL), one component layer
(existing CSS + tokens, or an approved headless lib), reusable loading/empty/error
patterns, and a minimal component gallery. **Signal:** a new page is composed from
existing patterns, not new CSS.

---

## Suggested order of attack

| Sprint | Items | Why first |
|---|---|---|
| Now | I-01, I-02, I-03, I-04 | Unblocks Phases 02–04; nothing else can start safely |
| Before Phase 05 | I-11, I-12, I-15, I-28 | Contract decisions that UI/API code will bake in |
| Before Phase 07/08 | I-05, I-17, I-18 | Ingestion, storage and cost controls must exist on day one |
| Continuous | I-06…I-10, I-13…I-16, I-19 | Rework prevention + production visibility |
| Whenever quiet | I-20…I-27 | Cheap, compounding hygiene |

**The one-line summary:** verify Postgres, close four blocking decisions
(OA-01/02/09 + CSRF), write the missing API/model contracts, then build — everything
else here is cheaper than the rework it prevents.
