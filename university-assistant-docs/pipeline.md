# Pipeline — University Smart Assistant

Every automated flow in the system, end to end. Where the current documentation is
vague or leaves a step implicit, the corrected flow is marked **P-nn** with the
reason. All flows assume the architecture in `architecture.md`.

---

## 1. Pipeline map

| # | Pipeline | Trigger | Owner | Failure mode |
|---|---|---|---|---|
| 1 | Document ingestion | admin upload | worker | retryable, per-document status |
| 2 | Question answering | student asks | API + provider | refuse or degrade, never invent |
| 3 | Conversation lifecycle | student actions | API | ownership-scoped |
| 4 | Data lifecycle / retention | schedule | worker | logged, reversible where possible |
| 5 | Development workflow | task start | developer/agent | phase gate blocks progress |
| 6 | CI | push / PR | CI | merge blocked |
| 7 | Release / CD | tag or manual promote | pipeline | rollback |
| 8 | Observability | continuous | platform | alert |
| 9 | AI evaluation / regression | prompt/model/chunk change | CI job | merge blocked |
| 10 | Security scanning | push / nightly | CI | merge blocked / alert |
| 11 | Backup & restore | schedule | platform | alert + restore drill |

---

## 2. Document ingestion pipeline

**P-01 — Asynchronous, resumable, idempotent.** `docs/06` §3 and Phase 07 describe
the stages but imply they run inside the request. They must not: a 50-page PDF with
embeddings takes tens of seconds to minutes.

```
[Admin] POST /api/v1/admin/documents/  (multipart + metadata)
   │
   ├─ 1. Request-time validation (fast, synchronous)
   │     extension + MIME + magic bytes + size cap + filename sanitisation
   │     → reject with VALIDATION_ERROR (Persian message)
   │     → store file in object storage, compute SHA-256 checksum
   │     → create Document(status=Uploaded, version=N, effective_from/to)
   │     → enqueue job(document_id)   ← idempotency key = checksum
   └─ 2. Respond 202 + status URL (never block on processing)

[Worker] job(document_id)
   Validating  → file present, checksum matches, not encrypted/corrupt
   Processing  → extract (page-aware) → clean → normalize_persian → chunk → metadata
   Embedding   → batch embed (retry with backoff on 429/5xx) → store vectors
   Indexed     → verify chunk count > 0 and dimension matches configuration
   Active      → per activation rule; previous version of the same logical
                 document → Superseded

Failure at any stage:
   status = Failed(reason_code, persian_message, stage, attempt)
   → retryable from the admin API without re-uploading
   → max 3 attempts, then park for manual action and raise an alert
```

Guarantees:

- **Idempotent** by checksum: re-uploading an identical file does not duplicate chunks.
- **Versioned**: a new version never deletes the old one; retrieval filters on `Active`.
- **Traceable**: every chunk keeps document id, version, page, section, index, token count, embedding model.
- **P-02 — Scanned/OCR-less pages are marked unsupported** instead of indexing noise; a silently empty index is worse than a visible gap.
- **No partial activation**: chunks are written transactionally per document, so a failed embedding run leaves no half-indexed version.
- **Metrics per stage**: duration, chunk count, token count, embedding calls, failures.
- **Re-index command** (`manage.py reindex --document-id|--all`) for prompt, model or normalizer changes; safe to run while serving traffic.

### 2.1 Chunking rules

| Rule | Value |
|---|---|
| Target size | ~800–1200 tokens with 10–15% overlap |
| Boundary respect | never split a clause mid-sentence; keep table rows together |
| Metadata per chunk | page, section title, chunk index, token count, document version |
| Normalization | applied before embedding **and** before storing searchable text (C-05) |
| Persian specifics | preserve meaningful ZWNJ, normalize digits, keep Persian separators |

---

## 3. Question answering pipeline

```
POST /api/v1/conversations/{id}/messages/   { content }
   │
   ├─ authn/authz: conversation belongs to the caller (queryset-scoped)
   ├─ persist user Message(role=USER)
   ├─ normalize_persian(content)                 ← same normalizer as ingestion
   ├─ QuestionRouter.classify()
   │      STRUCTURED | RAG | HYBRID | GENERAL | OUT_OF_SCOPE
   │      deterministic rules first, model second; both recorded
   ├─ Evidence gathering
   │      STRUCTURED   → ORM query, term-aware, no history mixing
   │      RAG          → vector search: top_k, similarity ≥ threshold,
   │                     filters: status=Active, effective period, doc type
   │      HYBRID       → both, kept as separately labelled blocks
   │      GENERAL      → no evidence (explanatory only)
   │      OUT_OF_SCOPE → refuse immediately, no provider call
   ├─ Evidence sufficiency check
   │      insufficient → Persian refusal + optional clarifying question
   │                    (no provider call, no invented facts)
   ├─ PromptService.build(version, evidence, question)    ← prompts are versioned
   ├─ LLMProvider.chat(timeout, retries, circuit breaker)
   │      provider failure → AI_PROVIDER_ERROR (503); conversation still saved
   ├─ CitationService.validate(answer, evidence)
   │      drop citations absent from the evidence set; flag if all were dropped
   ├─ persist Message(role=ASSISTANT, retrieval_mode, latency_ms)
   │   + MessageSource rows (chunk, label, page, section, score, citation text)
   └─ respond { message, sources[], warnings[] }
        (optional SSE streaming: tokens stream first, sources follow)
```

**P-03 — Evidence sufficiency is a gate, not a hope.** Refusal triggers on
(no results) OR (top score below threshold) OR (conflicting results). It is a
testable branch with a Persian message, not an emergent property of the prompt.

**P-04 — Routing must be observable and testable.** Persist the chosen mode and
whether a rule or the model decided it, so a wrong route is diagnosable and the
routing table can be unit-tested against labelled queries.

### 3.1 Degradation policy

| Failure | Behaviour |
|---|---|
| Provider down/timeout | `AI_PROVIDER_ERROR` (503), Persian message, question preserved, retry offered |
| Vector search down | HYBRID falls back to structured-only; otherwise `RETRIEVAL_ERROR` |
| Database down | `/health/ready` fails; requests return 503 without internals |
| Rate limit hit | `RATE_LIMITED` (429) with `retry_after_seconds` |
| Weak evidence | Persian refusal + clarifying question, never a fabricated fact |

The academic pages stay fully usable when only the AI provider is unavailable
(`docs/12` §5).

---

## 4. Lifecycle pipelines

### 4.1 Conversation

```
create → (ask → answer → sources)* → rename → archive (default) | hard delete (policy)
```
- Ownership checked on every access; another user's id returns 404.
- History paginated (newest-first cursor); index `(conversation, created_at)`.
- Archive is the default "delete" (recoverable); hard delete only via an explicit
  policy decision (OA-07) — `docs/14` requires that meaning to be documented.
- Retention job (Phase 15) deletes/archives per policy and logs the action.

### 4.2 Document

```
Uploaded → Validating → Processing → Indexed → Active → Superseded/Inactive → Archived
```
Archived documents keep metadata and audit trail; chunks are removed from retrieval
but not necessarily from storage until retention expires.

### 4.3 Academic data

```
admin CRUD (validated) → term-scoped rows → historical rows immutable
```
Rules: current-term operations never mutate past terms; exam/schedule changes are
audited; a new academic year is a new `AcademicTerm`, never an update of an old one.

### 4.4 Audit

Append-only for: document upload/activate/deactivate/delete, exam schedule changes,
role/permission changes, regulation version changes. No update or delete path in the
application layer; retention handled by an explicit archival job.

---

## 5. Development workflow pipeline

```
Phase gate (Definition of Ready)
   │
   ├─ read AGENTS.md → START-HERE → relevant docs → current phase → existing code
   ├─ write a short plan (files touched, tests, migrations)
   ├─ branch: feature/<phase>-<slug> | fix/<slug> | chore/<slug>
   ├─ implement smallest coherent change
   ├─ add/update tests (rules, permissions, contracts)
   ├─ local gate: ruff → pytest → makemigrations --check
   │              npm run typecheck → vitest → build
   ├─ update docs when a contract changed (+ ADR if architectural)
   ├─ open PR → CI runs → review against the phase acceptance criteria
   ├─ merge to main (main stays runnable)
   └─ Phase gate (Definition of Done) → checkpoint commit/tag
```

Rules that prevent the usual drift: one phase at a time; no post-MVP work during MVP
phases; no undocumented dependency; no API contract change without a docs update and
a schema diff.

---

## 6. CI pipeline

**P-05 — Six jobs, fail fast, cheapest first.**

| Order | Job | What it runs | Blocks merge |
|---|---|---|---|
| 1 | `lint` | ruff (backend), eslint/prettier if adopted (frontend) | ✅ |
| 2 | `typecheck` | `tsc --noEmit`; `python manage.py check` with `DEBUG=false` | ✅ |
| 3 | `backend-test` | pytest on **PostgreSQL + pgvector service** (not SQLite), with coverage of rules/permissions | ✅ |
| 4 | `migrations` | `makemigrations --check --dry-run`; apply forward + reverse on a scratch DB | ✅ |
| 5 | `contract` | generate OpenAPI; fail on unreviewed schema diff; validate examples | ✅ |
| 6 | `frontend-test` | vitest + Testing Library; MSW mocks | ✅ |
| 7 | `build` | production images build; frontend bundle size budget | ✅ |
| 8 | `e2e` (from Phase 14) | Playwright against compose stack (API + Postgres + fake provider) | ✅ |
| 9 | `security` | `pip-audit`, `npm audit`, secret scan, prompt-injection suite (from Phase 15) | ✅ |
| 10 | `eval` (from Phase 08) | RAG golden dataset run + thresholds | ✅ |

Also required: `docker compose config` validation (the compose file is currently
unverified), artifact upload (coverage, golden-set report, schema), and dependency
caching keyed on lockfiles.

**P-06 — Never test only on SQLite.** SQLite cannot express pgvector, partial unique
indexes, `CHECK` constraints or `pg_trgm`, i.e. most of what this system relies on.
The baseline's SQLite fallback stays for developer convenience only.

---

## 7. Release / CD pipeline

```
tag vX.Y.Z on main
  │
  ├─ build images (backend, frontend, worker) tagged with commit SHA
  ├─ push to registry
  ├─ deploy to staging → migrations → smoke tests → E2E
  ├─ manual promote (or auto on green) → production
  │      ├─ 1. backup database (verified completion)
  │      ├─ 2. run migrations as a separate job (not per-replica at startup)
  │      ├─ 3. roll out API + worker (rolling/blue-green)
  │      ├─ 4. roll out frontend static assets (immutable, hashed filenames)
  │      ├─ 5. readiness check on /health/ready
  │      ├─ 6. smoke test: health, login, one read endpoint, one grounded answer
  │      └─ 7. watch error rate + latency for a soak window
  └─ rollback: previous image + (if needed) reverse migration
```

Release requirements: migrations backward compatible for one release; no secret in
images; static assets versioned so a rollback is instant; runbook updated with the
exact commands; known limitations recorded (`docs/19` §3).

---

## 8. Observability pipeline

```
Request/job
   → request-id middleware (exists) ──┬─→ JSON access log ─→ log store ─→ search by request id
   │                                  ├─→ metrics counters/histograms ─→ Prometheus ─→ Grafana dashboards
   │                                  └─→ traces (optional) ─→ collector ─→ trace UI
   ├─ AI flow → mode, evidence count, top score, provider latency, tokens, model
   ├─ ingestion → stage, duration, chunks, failures
   └─ errors → code, path, request id (never internals or PII)

Alert rules → on-call notification → runbook link
Weekly: review SLO burn, top error codes, slowest routes, queue depth, provider cost
```

Dashboards to build in Phase 16: API (latency/error/throughput), database
(connections/slow queries), queue (depth/failure/retry), AI (latency/failure/tokens/
cost), ingestion (per-stage duration), business (questions/day, unanswered rate).

---

## 9. AI evaluation pipeline

```
Trigger: prompt | model | embedding | chunking | retrieval | normalizer change
   │
   ├─ run golden dataset (Persian): question → expected source/page/facts
   ├─ retrieval metrics: hit-rate@k, MRR, wrong-version rate
   ├─ generation metrics: factual consistency with evidence, citation integrity,
   │                      refusal correctness, Persian language quality
   ├─ compare to the stored baseline report → fail on regression beyond tolerance
   └─ store report as a CI artifact + record the prompt/model version used
```

`docs/15` §4 requires the rerun; automating it is what makes the requirement real.
The dataset must include negative cases (unsupported questions) so refusal quality is
measured, not assumed.

---

## 10. Security pipeline

| Stage | Check | Cadence |
|---|---|---|
| Pre-commit | secret scan (gitleaks-style), no `.env` staged | every commit |
| CI | `pip-audit`, `npm audit`, SAST on changed code | every PR |
| CI | prompt-injection suite against the assistant (malicious "regulation" documents) | every PR (from Phase 09) |
| CI | permission matrix test: every endpoint × every role | every PR |
| Nightly | full dependency audit, container image scan | nightly |
| Release | verify no secret in image layers; verify headers (HSTS/CSP) | every release |
| Periodic | rotate keys, review admin accounts, restore drill | quarterly |

Upload safety: files are never executed or served from a public path; PDF parsing
runs in the worker with resource limits (**P-07** — a decompression bomb must not
take the API down).

---

## 11. Backup and disaster recovery pipeline

```
nightly:  pg_dump (or pgBackRest WAL) → encrypt → off-host storage → retention (7d/4w/6m)
weekly:   verify restore into a scratch database → run smoke tests → record result
monthly:  full restore drill into staging → document duration and gaps
documents: object storage versioning + lifecycle policy (or rsync + checksums)
secrets:  backed up in the secret manager, never in the database dump
```

**P-08 — A backup that has never been restored is not a backup.** Phase 16's
criterion already demands a tested restore; the pipeline makes it recurring, and
records recovery time so an outage estimate exists.

---

## 12. Failure playbook (quick reference)

| Symptom | First check | Action |
|---|---|---|
| 5xx spike | error dashboard by code, request ids | roll back if a deploy correlates |
| Provider errors | provider status, latency, quota | circuit breaker already degrades; notify |
| Ask endpoint slow | retrieval latency, provider latency, token size | lower `top_k`, tighten prompt, add cache |
| Queue backlog | worker count, failure rate, job duration | scale workers, park poison jobs |
| Retrieval returns nothing | document `Active`? normalized text? dimension mismatch? | re-index the affected document |
| Wrong answers despite evidence | prompt version, citation validation output | fix prompt version, rerun golden set |
| DB connections exhausted | pool size vs worker count | tune pool, add pgbouncer |
| Disk full (vectors/logs) | growth rate of chunks + logs | retention job, log rotation |



