# Notifications API (Phase 12)

In-app notifications, one row per recipient. Read state is private to the
recipient by construction, so notifications can never be shared between users;
expired rows never appear in any active view (list, badge counters, mark-all).

## Data model (`apps.notifications`)

`Notification` — `user` (FK, recipient), `type` (`ANNOUNCEMENT` / `DEADLINE` /
`EXAM` / `SYSTEM`), `title`, `body`, `link` (app path for the frontend), `is_read`,
`read_at`, `expires_at` (nullable → never expires), `created_at`, and
`source_announcement` (nullable FK for traceability).

- Per-row fan-out is deliberate (docs/03 rationale: read state belongs to the
  recipient); uniqueness `(user, source_announcement)` (partial, when the
  source is set) makes re-publishing idempotent — republishing an announcement
  never creates a second copy for the same user.
- Indexes: `(user, is_read)` and `(user, expires_at)` serve the active
  unread/badge queries.
- `link` values are generated app paths only (e.g. `/announcements`); the
  frontend routes them, never injects them as raw HTML.

## GET `/api/v1/notifications/`

The caller's *active* notifications, newest first. "Active" = `expires_at` is
null **or** in the future; an expired row disappears from the list without
being deleted (historical record preservation).

- Auth: Bearer token (any role — professors/admins receive copies too).
- Query: `?unread=true` narrows server-side to unread rows; `page`,
  `page_size` per the standard pagination envelope.
- Response: paginated (`count`, `next`, `previous`, `results`); each row:

```json
{
  "id": 6,
  "type": "ANNOUNCEMENT",
  "title": "برنامه امتحانات اعلام شد",
  "body": "…",
  "link": "/announcements",
  "is_read": false,
  "read_at": null,
  "expires_at": "2026-12-01T00:00:00Z",
  "created_at": "2026-11-09T14:30:14Z"
}
```

## GET `/api/v1/notifications/unread-count/`

Badge counters and the mark-all button read this; expired rows are excluded.

```json
{ "unread_count": 3 }
```

## POST `/api/v1/notifications/{id}/mark-read/`

Persists one row's read state (`is_read`, `read_at`, `updated_at`). Authorised
by queryset scoping, never a client-side check: another user's pk is `404
NOT_FOUND` (anti-enumeration, planner contract). Idempotent.

Returns the serialised (now-read) row.

## POST `/api/v1/notifications/mark-all-read/`

Marks every *active unread* row read (`read_at` set per row). Returns
`{"updated": n}` with the number of rows changed; expired rows are never
touched.

## Errors

| Situation | Response |
|---|---|
| Unauthenticated | `401 AUTHENTICATION_REQUIRED` |
| Another user's notification pk | `404 NOT_FOUND` |
| Unknown pk | `404 NOT_FOUND` |

## Publishing: admin announcements → notifications

Announcements fan out into per-user notification rows when they become
published (`apps/announcements.views.AdminAnnouncementViewSet`):

- On create with `is_published: true`, and on update **only** on the
  unpublished → published transition (editing a published announcement is not a
  re-dispatch; unpublishing does not retract delivered copies).
- Recipients mirror the public feed's audience rules (C-03) exactly:
  department-targeted rows go to that department's students; faculty-targeted
  rows go to the faculty's students **and** every active user without a student
  profile (professors/admins, matching the feed's audience predicate);
  unrestricted rows go to every active user.
- `type=ANNOUNCEMENT`, `title/body` copied, `link=/announcements`,
  `expires_at` inherited from the announcement.

## Deadline-trigger design (documented, not implemented)

Notifications exist as an infrastructure surface, but no trigger runs yet —
`docs/14` (data lifecycle) requires retention and de-dup rules for any
automation. Design for a future management command (`manage.py
dispatch_deadlines`), run by cron/Celery beat:

1. **Sources (scoped, term-aware):**
   - `apps.calendar.AcademicEvent` with `event_type` in (`DEADLINE`,
     `REGISTRATION`) where `starts_at` is inside the notification window and
     `is_published`.
   - `apps.exams.Exam` rows with an upcoming date/time.
   - Enrolment-scoped events filter receivers by `students.StudentProfile` of
     the event's term; exam rows can target the offering's enrolled students
     (fallback: department students when there is no enrolment data).
2. **Lead times:** typical design — T-7d, T-3d, T-1d, day-of (configurable via
   settings); each lead time is one notification (`type=DEADLINE`/`EXAM`,
   `title` = event title, `body` = human summary, `link` = `/calendar` or
   `/exams`, `expires_at` = event end).
3. **De-duplication:** the same `(user, type, dedup_key)` triple must not
   repeat. Reuse the Phase 12 pattern: a partial `UniqueConstraint` on
   `(user, dedup_key)` computed as f"{source_model}:{source_pk}:{lead}", plus
   `bulk_create(ignore_conflicts=True)` so re-running the command is safe and
   idempotent.
4. **C-1 honest-content rule:** notifications state only facts that exist in
   the database (never invented deadlines); Persian wording mirrors the
   calendar/exams wording.
5. **Retention:** expired rows stay queryable by pk but are excluded from all
   "active" surfaces; a later retention task may prune rows older than one
   academic year.

Known limitation for this phase: reminders appear **only** when an
announcement is published or a row is created through the service
(`apps.notifications.services.create_notification`); no scheduled command
exists yet by design (post-MVP automation, tracked above).
