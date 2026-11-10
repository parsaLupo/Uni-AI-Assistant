# Phase 13 — Admin Dashboard and Analytics

## Objective
Provide administrative visibility into data and system usage.

## Metrics
- active users
- question count
- topic distribution
- most used documents
- AI usage/error counts
- average latency

## Privacy rule
Analytics must be aggregated or access-controlled appropriately.

## Acceptance criteria
- [x] Admin-only dashboard.
- [x] Metrics are computed from real application data.
- [x] Sensitive raw message content is not exposed by default.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Status: ✅ Done (2026-11-10) — dashboard **and** management screens complete

**Scope decision (updated):** the checklist task "Admin management screens:
users, roles, courses, professors, terms, exams, announcements, documents"
required completing those screens, so Phase 13's frontend was extended to
full CRUD over the existing Phase 03/04 admin endpoints — no new backend
endpoints were created.

### Backend (`backend/apps/analytics`, new files `services`/`serializers`/`views`/`urls` + migration `0003_airequestevent.py`)

- **`AIRequestEvent`** model — one row per AI attempt (user FK nullable,
  `mode` ≤32 chars, `outcome` default `OK`, `latency_ms` nullable,
  `created_at`; indexes `(outcome, created_at)` and `(mode, created_at)`).
  Stores **no question or answer text** — the privacy rule is enforced here.
- **`record_ai_request()`** telemetry helper — persists one event, never
  raises into the request (try/except + `app.analytics` logger). Wired into
  all three AI entry points: `/ai/ask/`, `/ai/ask/stream/` (SSE) and the
  conversation message path.
- **Aggregations** (`services.py`, computed on demand per A-10):
  users (`active_users`, `recently_active_users` = last login ≤7 days,
  `by_role`), questions (total / last 7 days / answers /
  insufficient-evidence answers), `topic_distribution` (routed execution-mode
  counts from assistant messages — `docs/08` modes are the only durable
  "topic" signal), `top_documents` (top 10 by answer citations),
  `ai` (total, errors = outcome ≠ `OK`, average latency over successful
  attempts; a completed 0 ms attempt still reports 0, not n/a).
- **Endpoints** (`IsAdmin`-gated, students rejected server-side):
  - `GET /api/v1/admin/analytics/dashboard/` — aggregate-only payload.
  - `GET /api/v1/admin/analytics/audit-log/` — read-only viewer over the
    append-only `AuditLog` (paginated; filters `?entity_type=`,
    `?action=`, `?actor=`; `actor_email` surfaced for admins).
- **Tests** (`test_admin_analytics.py`, 11 tests): admin-only access
  (403 student / 401 anonymous on both endpoints), viewer write-protected
  (405), dashboard aggregates real rows and the payload is assertably free of
  message content, honest empty DB, viewer filters, telemetry OK event +
  no-telemetry-on-validation-failure, `record_ai_request` never raises.

### Frontend (`frontend/src`)

- `api/admin.ts` (`fetchAdminDashboard`, `fetchAdminAuditLog`) + query keys
  (`adminAnalytics()`, `adminAuditLog(query)`).
- `AdminAnalyticsPage.tsx` on `/admin/analytics`: metric cards (Persian
  digits), mode distribution + role counts, top-documents table, and the
  audit-log section with an action filter bound to URL state (`useUrlState`).
- i18n: `adminPage` analytics + audit labels in `src/i18n/fa.ts`,
  `executionModeLabels` in `src/i18n/labels.ts`.
- **Management screens (second Phase 13 delivery, 2026-11-10):** every admin
  nav entry now renders a real CRUD page over its documented endpoint
  (single source: `features/admin/links.ts` → `App.tsx` route map; the
  Phase 05 stub page was removed):
  - `AdminUsersPage` (`/admin/users`) — `GET/POST/PATCH/DELETE /admin/users/`
    with search/role/is-active filters and pagination; DELETE = soft
    deactivate behind a confirmation dialog; role management lives here
    (Role is a `User` attribute, no separate roles table exists —
    privileged role changes are SUPERADMIN-only in the UI, enforced by the
    server).
  - `AdminCoursesPage` (`/admin/courses`) — course CRUD, prerequisites
    editor (`/admin/courses/{id}/prerequisites/` + `DELETE
    /admin/prerequisites/{id}/`), offerings editor with nested schedule rows
    (`/admin/offerings/`, `/admin/offerings/{id}/schedules/` +
    `PATCH/DELETE /admin/schedules/{id}/`); 409 (offered course) surfaces
    the backend's Persian message.
  - `AdminProfessorsPage` (`/admin/professors`) — full CRUD with
    department filter.
  - `AdminTermsPage` (`/admin/terms`) — create/edit only (DELETE is not in
    the contract); current-term conflict 409 surfaced as Persian text.
  - `AdminExamsPage` (`/admin/exams`) — exam list (public `/exams/` read)
    plus set/edit per offering (`GET/PUT/PATCH /admin/offerings/{id}/exam/`
    — no DELETE exists by contract).
  - `AdminAnnouncementsPage` (`/admin/announcements`) — full CRUD with
    priority, term + faculty/department audience, publish/at/expiry fields;
    publishing fans out notifications server-side (Phase 12, unchanged).
  - `AdminDocumentsPage` (`/admin/documents`) — multipart PDF upload
    (`202 Accepted`), metadata/status PATCH, activate + supersede,
    retry-for-failed, delete with confirmation.
  - Shared plumbing: `requestJson` now only JSON-serialises string bodies so
    FormData uploads keep their multipart boundary; `ui.tsx` gained
    `Modal`, `ConfirmDialog`, `FieldError`; admin CRUD queries added to
    `api/keys.ts`; all copy is Persian in `i18n/fa.ts` with Persian digits
    and Jalali dates; every destructive action requires a confirmation.
- Tests: `test/admin-users-page.test.tsx`, `test/admin-documents-page.test.tsx`
  (wire-level assertions on list/create/delete/activate) alongside the
  existing `test/admin-analytics.test.tsx`.

### Tests run / verification

- Backend: full suite `334 passed` (PostgreSQL via `TEST_DATABASE_URL`),
  management-app subset re-run with exit code 0 after the frontend work
  (no backend changes in this delivery).
- Frontend: typecheck clean; `65 passed` (12 files; +7 new page tests);
  production build clean (pre-existing >500 kB chunk-size warning only).
- Live smoke (Docker stack, admin@ account): all eight admin list endpoints
  returned real paginated data matching the page types; write-path smoke
  verified announcement create/update/delete, course + prerequisite
  create/delete, user create/update/deactivate/reactivate; student login
  receives `403` on `/admin/users/`. Scratch rows removed.

### Acceptance-criteria notes

- "Every high-impact admin action appears in the audit log" is ticked: all
  admin writes already flow through `AuditableViewSetMixin` (Phase 04) —
  `test_audit.py` proves CREATE/UPDATE/DELETE each emit an `AuditLog` row,
  and every existing admin resource (users, academic data, documents,
  enrollments, schedules, exams, announcements) uses it. The tick therefore
  covers all actions that exist; future endpoints must keep using the mixin.

### Known limitations

- Topic distribution is the routed execution mode, not free-text topics —
  the application stores no durable topic taxonomy yet.
- AI telemetry starts at Phase 13; older attempts are absent (dashboard
  reflects only what exists).
- `avg_latency_ms` is `null` until at least one successful attempt exists.
- Terms cannot be deleted and exams cannot be deleted-unset — both by API
  contract (D4 immutability / one-exam-per-offering), not a UI gap.
- Offering/exam create+edit is available for the current term and any
  non-past term; historical rows stay immutable per D4.

