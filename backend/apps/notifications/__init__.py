"""Notifications (architecture.md section 3.2: app `notifications` → `/notifications/*`).

User-scoped in-app notifications: one row per recipient, each carrying its own
read state, so read/unread can never be shared between users. Rows have an
optional `expires_at` — expired rows never appear in active lists
(docs/api/admin.md: "expiry honoured by list endpoints").
"""
