# Admin API Catalog

Status: contract defined in Phase 01; implemented in Phase 04.
Source of truth for shapes is the generated `openapi.yaml` (ADR-012) — this file
is the human catalog and the permission matrix. Every endpoint here follows the
global rules in `docs/04-api-specification.md`: versioned under `/api/v1/`,
paginated lists (`?page=&page_size=`), documented filters only, the standard
error envelope, and server-side authorization.

## Common rules (apply to every endpoint below)

- **Permissions:** `ADMIN` unless stated. For users specifically: listing,
  reading and creating **non-privileged** accounts is `ADMIN`; creating or changing a
  role to `ADMIN`/`SUPERADMIN`, and deactivating any privileged account, requires
  `SUPERADMIN`; nobody may deactivate their own account (`409 CONFLICT`).
  Authorization is enforced in Django — UI visibility is never sufficient.
- **Writes are audited:** create/update/delete emit an `AuditLog` row (actor,
  action, entity, before/after ids) per `docs/07` §7.
- **Uniqueness conflicts return `409 CONFLICT`**, validation failures `400
  VALIDATION_ERROR` with field details, auth failures `401`/`403` as documented.
- **Creates return `201`, deletes `204`, no-content patches `200`.**
- **Only serializers are returned** — never database models.
- Term-scoped resources always accept/return `term`; historical rows are immutable
  (a new academic year creates a new `AcademicTerm`, never edits an old one).

## Users and students (Phase 03/04)

| Method | Endpoint | Purpose | Notes |
|---|---|---|---|
| GET | `/admin/users/` | List users | filters: `?search=`, `?role=`, `?is_active=` |
| POST | `/admin/users/` | Create user | password write-only; `role` required |
| GET/PATCH/DELETE | `/admin/users/{id}/` | Manage one user | role change = `SUPERADMIN`; delete = deactivate |
| GET | `/admin/students/` | List student profiles | filters: `?faculty=`, `?department=`, `?search=` |
| GET/PATCH | `/admin/students/{id}/` | Edit profile fields | grade/history edits go through enrollments |

## Academic structure (Phase 04)

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/admin/faculties/` | List/create faculties |
| GET/PATCH/DELETE | `/admin/faculties/{id}/` | Manage one faculty |
| GET/POST | `/admin/departments/` | List/create departments (`?faculty=`) |
| GET/PATCH/DELETE | `/admin/departments/{id}/` | Manage one department |
| GET/POST | `/admin/courses/` | List/create courses (`?department=`, `?search=`) |
| GET/PATCH/DELETE | `/admin/courses/{id}/` | Manage one course |
| GET/POST | `/admin/courses/{id}/prerequisites/` | Read/add prerequisites |
| DELETE | `/admin/prerequisites/{id}/` | Remove a prerequisite edge |
| GET/POST | `/admin/professors/` | List/create professors |
| GET/PATCH/DELETE | `/admin/professors/{id}/` | Manage one professor |
| GET/POST | `/admin/terms/` | List/create academic terms |
| GET/PATCH | `/admin/terms/{id}/` | Edit a term | only the *current* term may be flagged; enforced by DB constraint |

## Offerings, schedules, exams (Phase 04)

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/admin/offerings/` | List/create course offerings (`?term=`, `?course=`, `?professor=`) |
| GET/PATCH/DELETE | `/admin/offerings/{id}/` | Manage one offering |
| GET/POST | `/admin/offerings/{id}/schedules/` | Read/add class schedule rows |
| PATCH/DELETE | `/admin/schedules/{id}/` | Edit/remove one schedule row |
| GET/PUT/PATCH | `/admin/offerings/{id}/exam/` | Set exam for an offering | one exam per offering (DB constraint) |
| GET/POST | `/admin/enrollments/` | Manage enrollments/grades | `?student=`, `?term=`, `?status=` |
| PATCH/DELETE | `/admin/enrollments/{id}/` | Correct or remove an enrollment | grade changes audited |

## Calendar and announcements (Phase 04)

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/admin/calendar/events/` | List/create academic events (`?term=`) |
| GET/PATCH/DELETE | `/admin/calendar/events/{id}/` | Manage one event |
| GET/POST | `/admin/announcements/` | List/create announcements |
| GET/PATCH/DELETE | `/admin/announcements/{id}/` | Manage one announcement | expiry honoured by list endpoints |

Announcement publication (Phase 12): creating with `is_published: true`, or
updating to published, fans out one user-scoped notification per recipient
(feed audience semantics, idempotent on republish). See
`docs/api/notifications.md`.

## Documents and analytics (already in `docs/04` §6)

- `POST/GET /admin/documents/`, `GET/PATCH/DELETE /admin/documents/{id}/` — see `docs/api/documents.md`.

### Analytics (Phase 13)

Both endpoints are `ADMIN`/`SUPERADMIN`-only and **aggregate-only**: the query
layer never selects raw message content, so no payload can leak student chats
(`docs/13` Phase 13 privacy rule, enforced in the services layer — not in the UI).

| Method | Endpoint | Purpose | Details |
|---|---|---|---|
| GET | `/admin/analytics/dashboard/` | Admin metrics from real application data | see payload below |
| GET | `/admin/analytics/audit-log/` | Read-only viewer over the append-only `AuditLog` | filters `?entity_type=` (full label or bare model), `?action=CREATE/UPDATE/DELETE/RETRY`, `?actor=<user id>`; paginated |

`GET /admin/analytics/dashboard/` payload (all values computed on demand, per
A-10 — no materialisation):

- `users`: `active_users` (active accounts), `recently_active_users` (last login
  within 7 days), `by_role[]` (`role`, `count`).
- `questions`: `total` (student questions), `last_7_days`, `answers`,
  `insufficient_evidence` (answers that reported missing evidence).
- `topic_distribution[]`: routed execution-mode counts (`STRUCTURED`/`RAG`/
  `HYBRID`/`GENERAL`/`OUT_OF_SCOPE`) — the documented `docs/08` modes are the
  only durable "topic" signal the application stores.
- `top_documents[]`: top 10 documents by answer citations (`id`, `title`,
  `document_type`, `academic_year`, `citation_count`).
- `ai`: AI usage telemetry (`total_requests`, `error_count`,
  `avg_latency_ms`, `null` when no successful attempt exists yet). One row per
  attempt is recorded at the AI entry points (`/ai/ask/`, `/ai/ask/stream/`,
  conversation messages) with mode, outcome code and latency — never question
  or answer text.
- `documents_total`, `generated_at` (ISO-8601).

AI telemetry lives in the `AIRequestEvent` table (`apps.analytics`). It is
telemetry, not an audit record; the audit log remains write-only for the API —
the viewer above is its only read surface.

## Explicitly out of scope for this catalog

- Course *eligibility* decisions (Phase 11) — the engine reads data, it is not a resource.
- RAG/document processing internals (Phase 07/08) — exposed only as document status.
- Conversation content of other users: admins never read raw student chats by
  default (`docs/13` Phase 13 privacy rule); only aggregates.
