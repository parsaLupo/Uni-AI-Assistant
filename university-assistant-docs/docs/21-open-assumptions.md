# 21 — Open Assumptions and Undecided Rules (Phase 00 baseline)

Phase 00 task "Identify open assumptions" produced this list. Per
`START-HERE.md`, the agent must not guess a rule when the decision materially
affects data or security — each item below therefore states the assumption the
current baseline uses, and the phase that must confirm or replace it.

Legend — **Status**: `ACCEPTED` = safe working assumption, may be corrected with
low cost. `DECISION NEEDED` = must be answered before the listed phase starts.

| ID | Question / assumption | Baseline assumption today | Blocking phase | Status |
|---|---|---|---|---|
| OA-01 | Is student registration open or admin-provisioned? (FR-AUTH-001 says "according to project policy") | Accounts are created by an admin; `/register` exists in `docs/20-ui-navigation.md` but no policy is written | Phase 02 | DECISION NEEDED |
| OA-02 | Login identifier: email or username? (`docs/03-database-design.md` says "email/username according to policy") | Custom user model keyed on a unique `username` field, email optional | Phase 02 | DECISION NEEDED |
| OA-03 | How do roles relate to `is_staff`/`is_superuser`? | `role` enum (`STUDENT`/`PROFESSOR`/`ADMIN`/`SUPERADMIN`) is authoritative for app permissions; `is_staff` only gates Django admin, which is disabled | Phase 02 | ACCEPTED |
| OA-04 | Is the Django admin UI part of the MVP admin surface? | No: admin works through `/api/v1/admin/` REST endpoints; `django.contrib.admin` is not installed | Phase 04 | DECISION NEEDED |
| OA-05 | Which LLM and embedding provider/model? Embedding dimension fixes the pgvector column | Unset (`AI_PROVIDER`, `AI_MODEL`, `EMBEDDING_MODEL` read from env; health reports `ai_provider: not_configured`) | Phase 06 | DECISION NEEDED |
| OA-06 | Does CI need PostgreSQL? | No: tests run on SQLite via `conftest.py` forcing `DATABASE_URL=""`; pgvector-specific SQL is untested | Phase 06 | DECISION NEEDED |
| OA-07 | Retention period for chat messages, audit logs, uploaded documents (`docs/07-security.md` section 6 requires this before production) | No retention/deletion implemented | Before production | DECISION NEEDED |
| OA-08 | Upload limits and allowed types beyond PDF; storage backend for documents | Not implemented (no upload endpoint yet) | Phase 05 | DECISION NEEDED |
| OA-09 | Concrete rate limits for auth and AI endpoints ("where appropriate") | No throttling configured | Phase 02 (auth), Phase 07 (AI) | DECISION NEEDED |
| OA-10 | Is course/professor content Persian-only, or is localized storage required? | Single `title`/`name` text fields, no per-language duplicates | Phase 03 | ACCEPTED |
| OA-11 | `AcademicTerm.is_current` — may more than one term be current? | Assumed at most one; must be enforced by a constraint, not by convention | Phase 03 | DECISION NEEDED |
| OA-12 | Grade scale and type for `Enrollment.grade` | Not yet modeled; the eligibility engine assumes a numeric 0–20 scale | Phase 09 | DECISION NEEDED |
| OA-13 | Pagination defaults | `page_size=20`, `max_page_size=100`, DRF `count/next/previous/results` shape | — | ACCEPTED |
| OA-14 | Time handling | Database stores UTC (`USE_TZ=True`); Persian display/`Asia/Tehran` conversion is a frontend concern | Phase 04 | ACCEPTED |
| OA-15 | Correlation header name | `X-Request-ID`, echoed; unsafe inbound values are replaced | — | ACCEPTED |
| OA-16 | Error code list extensions | `METHOD_NOT_ALLOWED` and `REQUEST_FAILED` added (ADR-009) | — | ACCEPTED |
| OA-17 | Where does "current term" come from when a student asks without specifying one? | Queries default to `AcademicTerm.is_current`; history is never silently mixed (`docs/17-domain-rules.md`) | Phase 07 | ACCEPTED |

## Rule for closing an item

Move a row to `ACCEPTED` (or delete it) by writing the decision into the
relevant design document and, when it changes an architectural boundary, into a
new ADR — as required by `docs/10-development-workflow.md` section 5.
