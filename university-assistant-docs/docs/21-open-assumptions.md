# 21 — Open Assumptions and Undecided Rules (Phase 00 baseline)

Phase 00 task "Identify open assumptions" produced this list. Per
`START-HERE.md`, the agent must not guess a rule when the decision materially
affects data or security — each item below therefore states the assumption the
current baseline uses, and the phase that must confirm or replace it.

Legend — **Status**: `ACCEPTED` = safe working assumption, may be corrected with
low cost. `DECISION NEEDED` = must be answered before the listed phase starts.

| ID | Question / assumption | Baseline assumption today | Blocking phase | Status |
|---|---|---|---|---|
| OA-01 | Is student registration open or admin-provisioned? (FR-AUTH-001 says "according to project policy") | **Decided (ADR-014):** self-service registration is open and always creates role `STUDENT`; `PROFESSOR`/`ADMIN`/`SUPERADMIN` accounts are created only by an admin. `/register` stays a public route | Phase 03 | ACCEPTED |
| OA-02 | Login identifier: email or username? (`docs/03-database-design.md` says "email/username according to policy") | **Decided (ADR-014):** login identifier is the email address — `USERNAME_FIELD="email"`, API field `email`; no separate username | Phase 03 | ACCEPTED |
| OA-03 | How do roles relate to `is_staff`/`is_superuser`? | `role` enum (`STUDENT`/`PROFESSOR`/`ADMIN`/`SUPERADMIN`) is authoritative for app permissions; `is_staff` only gates Django admin, which is disabled | Phase 02 | ACCEPTED |
| OA-04 | Is the Django admin UI part of the MVP admin surface? | No: admin works through `/api/v1/admin/` REST endpoints; `django.contrib.admin` is not installed | Phase 04 | DECISION NEEDED |
| OA-05 | Which LLM and embedding provider/model? Embedding dimension fixes the pgvector column | Unset (`AI_PROVIDER`, `AI_MODEL`, `EMBEDDING_MODEL` read from env; health reports `ai_provider: not_configured`) | Phase 06 | DECISION NEEDED |
| OA-06 | Does CI need PostgreSQL? | No: tests run on SQLite via `conftest.py` forcing `DATABASE_URL=""`; pgvector-specific SQL is untested | Phase 06 | DECISION NEEDED |
| OA-07 | Retention period for chat messages, audit logs, uploaded documents (`docs/07-security.md` section 6 requires this before production) | No retention/deletion implemented | Before production | DECISION NEEDED |
| OA-08 | Upload limits and allowed types beyond PDF; storage backend for documents | Not implemented (no upload endpoint yet) | Phase 05 | DECISION NEEDED |
| OA-09 | Concrete rate limits for auth and AI endpoints ("where appropriate") | **Decided (ADR-014):** `auth_ip=10/min` for login+register per IP, `auth_refresh=30/min` per user (IP fallback when the token is unverifiable); AI limits remain open for Phase 07 | Phase 03 (auth) | ACCEPTED (AI part open, Phase 07) |
| OA-10 | Is course/professor content Persian-only, or is localized storage required? | Single `title`/`name` text fields, no per-language duplicates | Phase 03 | ACCEPTED |
| OA-11 | `AcademicTerm.is_current` — may more than one term be current? | Assumed at most one; must be enforced by a constraint, not by convention | Phase 03 | DECISION NEEDED |
| OA-12 | Grade scale and type for `Enrollment.grade` | Not yet modeled; the eligibility engine assumes a numeric 0–20 scale | Phase 09 | DECISION NEEDED |
| OA-13 | Pagination defaults | `page_size=20`, `max_page_size=100`, DRF `count/next/previous/results` shape | — | ACCEPTED |
| OA-14 | Time handling | Database stores UTC (`USE_TZ=True`); `Asia/Tehran` and Jalali conversion is a frontend/display concern (see OA-18) | Phase 04 | ACCEPTED |
| OA-15 | Correlation header name | `X-Request-ID`, echoed; unsafe inbound values are replaced | — | ACCEPTED |
| OA-16 | Error code list extensions | `METHOD_NOT_ALLOWED` and `REQUEST_FAILED` added (ADR-009) | — | ACCEPTED |
| OA-17 | Where does "current term" come from when a student asks without specifying one? | Queries default to `AcademicTerm.is_current`; history is never silently mixed (`docs/17-domain-rules.md`) | Phase 07 | ACCEPTED |

| OA-18 | Jalali (Shamsi) date presentation: which library, and does the API format dates or only return instants (`docs/02`, `docs/11` now require Jalali "where required") | API returns ISO-8601 UTC instants; no Jalali formatting or date library exists yet | Phase 03 (term dates), Phase 05 (UI) | DECISION NEEDED |
| OA-19 | Persian text normalization for search and RAG (ی/ي, ک/ك, نیم‌فاصله, Persian vs Latin digits, common word forms) — applied at index time, query time, or both, and implemented in PostgreSQL or Python (`docs/11`, Phase 09 requirements) | No normalization anywhere yet; retrieval is unimplemented, so no index contract is fixed | Phase 09 | DECISION NEEDED |
| OA-20 | Persian webfont: self-host Vazirmatn (licence, subset, build size) or rely on system fonts (`docs/02` "Persian typography") | System stack only — `Vazirmatn` if locally installed, else `Tahoma`/`Segoe UI`; no font files or CDN added in the baseline | Phase 05 | DECISION NEEDED |
| OA-21 | Is the UI Persian-only, or must a user be able to switch language? (`docs/11` says Persian; no bilingual requirement is written) | Persian-only: no language switcher, no runtime i18n dependency; strings centralized in `frontend/src/i18n/fa.ts` so a switcher can be added later (ADR-010) | Before production | ACCEPTED |
| OA-22 | Who translates framework-generated messages (DRF validation/auth): DRF's bundled `fa` catalog or project-owned gettext catalogs | DRF/Django `fa` catalogs via `LANGUAGE_CODE="fa"`, pinned by `test_framework_validation_details_are_persian` (ADR-010); project sentences are Persian literals | — | ACCEPTED |
| OA-23 | CSRF strategy for the cookie-based refresh/logout endpoints (ADR-004 said CSRF "must be tested") | **Decided (ADR-014):** double-submit cookie — login sets a readable `csrftoken`, the client echoes it in `X-CSRFToken`, and `csrf_protect` guards refresh + logout; failure returns `403 PERMISSION_DENIED` | Phase 03 | ACCEPTED |
| OA-24 | Per-term credit limit for the Phase 11 selection engine (no documented number anywhere) | Working default **20 credits/term** (`COURSE_SELECTION_MAX_TERM_CREDITS`, `apps/students/course_selection.py:credit_limit()`); "exactly at the limit" is allowed, anything above rejected as `CREDIT_LIMIT_EXCEEDED` | Registrar to confirm the official value | ACCEPTED |

## Rule for closing an item

Move a row to `ACCEPTED` (or delete it) by writing the decision into the
relevant design document and, when it changes an architectural boundary, into a
new ADR — as required by `docs/10-development-workflow.md` section 5.
