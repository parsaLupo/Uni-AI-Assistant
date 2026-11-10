# Phase 12 — Notifications

## Objective
Deliver useful in-app academic notifications.

## Tasks
- notification model/API
- read/unread state
- admin-created announcements/notifications
- deadline-trigger design for future automation

## Acceptance criteria
- [x] Notifications are scoped to a user when applicable.
- [x] Read state persists.
- [x] Expired items do not appear as active.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

---

## Implementation record (2026-11-09)

### Backend — new app `apps.notifications` (architecture.md §3.2: `notifications` → `/notifications/*`)

| File | Role |
|---|---|
| `apps/notifications/models.py` | `Notification` (per-recipient copy): `user`, `type` (`ANNOUNCEMENT`/`DEADLINE`/`EXAM`/`SYSTEM`), `title`, `body`, `link`, `is_read`, `read_at`, `expires_at`, `source_announcement`; indexes `(user, is_read)` + `(user, expires_at)`; partial `UniqueConstraint (user, source_announcement)` = idempotent republish |
| `apps/notifications/services.py` | `announcement_recipients` (feed semantics C-03), `dispatch_announcement` (`bulk_create(ignore_conflicts=True)`, skips already-notified users), `create_notification`, `active_notifications` (non-expired only), `unread_count` |
| `apps/notifications/serializers.py` / `views.py` / `urls.py` | `GET /notifications/` (paginated, `?unread=true`), `GET /notifications/unread-count/`, `POST /notifications/{id}/mark-read/`, `POST /notifications/mark-all-read/` |
| `apps/notifications/migrations/0001_initial.py` | initial migration (applied to dev DB) |
| `apps/announcements/views.py` | fan-out hook: `perform_create` dispatches, `perform_update` dispatches only on unpublished→published transition |
| `config/settings.py` / `config/urls.py` | app + routes registered |
| `backend/openapi.yaml` | regenerated (`drf-spectacular`, views annotated with `@extend_schema`) |

Authorisation = queryset scoping (never client checks): another user's pk →
`404 NOT_FOUND`, planner contract. Read state is per-user by construction:
each recipient owns a row, so no read state can leak across users.

### Frontend

| File | Role |
|---|---|
| `src/api/notifications.ts` | typed client (list / unread-count / mark-read / mark-all-read) |
| `src/api/keys.ts` | `queryKeys.notifications(query)`, `queryKeys.unreadCount()` |
| `src/features/notifications/NotificationsPage.tsx` + `index.ts` | `/notifications` page: active rows, `?unread=true` scope select, per-row + mark-all read mutations (invalidate list + badge), Persian type labels, expiry display |
| `src/features/notifications/NotificationBell.tsx` | top-bar bell with unread badge, polled every 60s |
| `src/components/AppShell.tsx` | nav item «یادآوری‌ها» + bell in the header |
| `src/i18n/fa.ts`, `src/i18n/labels.ts` | Persian strings (`notificationsPage`, nav item, `notificationTypeLabels`) |
| `src/test/notifications-page.test.tsx` | 7 page tests (render, mark-one, mark-all, scope filter, empty + error states) |

### Tests run
- Backend: `pytest` with `TEST_DATABASE_URL` (PostgreSQL): **326 passed** (12 new
  notifications tests + full regression incl. Phase 11's 46).
- Frontend: `npm test` **55 passed (9 files)**; `npm run typecheck` clean.
- `ruff check backend/apps/notifications backend/apps/announcements/views.py` clean.
- Live (compose): applied `0001_initial` in the container, then exercised login →
  empty list/badge → announcement fan-out (unread count +1) → `mark-read`
  (read_at persisted, badge 1→0) → `mark-all-read` → `401` unauthenticated.
  Verification data removed afterwards.

### Acceptance criteria (task list)
- [x] Notification model (type, title, body, link, is_read, created_at, expires_at) + API.
- [x] Read/unread state, mark-all-read, badge count.
- [x] Admin-created announcements surfaced as notifications (idempotent fan-out on publish).
- [x] Expiry: expired items never appear as active (tested).
- [x] Deadline-trigger design documented (`docs/api/notifications.md`) for later automation.

### Known limitations
- No scheduled deadline resend yet: reminders fire on announcement publish or
  explicit service calls; the management-command design lives in
  `docs/api/notifications.md` (post-MVP automation).
- Delivered copies are not retracted when an announcement is unpublished;
  `expires_at` inheritance is the control for retirement.
- Unread counts poll every 60s (no push/WebSocket channel in this phase).
