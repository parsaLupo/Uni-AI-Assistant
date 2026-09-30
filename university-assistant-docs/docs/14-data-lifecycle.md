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

A retention policy should be defined before production use. Deleting a conversation should have a documented meaning: hard delete, soft delete, or archival.

## Audit logs

Audit logs should be append-oriented and protected from ordinary content edits.
