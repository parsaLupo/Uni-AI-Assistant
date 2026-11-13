# 14 — Data Lifecycle

## Academic data

Academic entities are managed by administrators or future authorized integrations. Historical records should be retained when they are needed to explain past terms.

## Documents

```text
Uploaded
  -> Validating
  -> Processing
  -> Indexed
  -> Active
  -> Superseded/Inactive
  -> Archived
```

## Chat messages

Decided in Phase 15 (OA-07): chat conversations are personal data.

- An **archived** conversation is **hard-deleted** `RETENTION_CONVERSATION_DAYS`
  days (default 180) after `archived_at`. Deleting a conversation therefore has
  a single documented meaning: permanent removal, cascading to its messages and
  message sources (`on_delete=CASCADE`).
- Implementation: `manage.py apply_retention --yes` (schedule it daily in
  production). `--dry-run` reports what would be deleted; without `--yes` the
  command refuses to delete anything. Behaviour tests:
  `apps/conversations/tests/test_retention.py`.
- Unarchived conversations are never touched by retention.

## Documents

Uploaded documents are **official university records** and are **retained**;
the lifecycle above (superseded/inactive/archived) governs their visibility,
not deletion. A document is deleted only by an explicit admin action, which is
audited.

## Audit logs

Audit logs are **append-only**: the application creates records and provides
no deletion or content-edit path, so the history of admin actions survives
retention of personal chat data.

## Telemetry

AI request telemetry rows (`apps.analytics`) record user id, outcome and
latency — no question/answer text — and follow the same application lifetime
as audit logs; they are not deleted by retention.
