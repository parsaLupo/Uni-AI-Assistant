# 10 — Development Workflow

## 1. Branching

Recommended pattern:

```text
main
  |
  +-- feature/...
  +-- fix/...
  +-- chore/...
```

The exact Git strategy can be simplified for a solo project, but `main` should remain runnable.

## 2. Work item lifecycle

```text
Planned
  -> In Progress
  -> Implemented
  -> Tested
  -> Reviewed
  -> Done
```

## 3. Agent workflow

For every task:

### Step 1 — Context

Read:

- `AGENTS.md`
- relevant architecture document
- current phase document
- affected code

### Step 2 — Plan

Write a small implementation plan before editing.

### Step 3 — Implement

Make focused changes.

### Step 4 — Verify

Run tests and inspect changed behavior.

### Step 5 — Document

Update docs if the behavior/contracts changed.

### Step 6 — Report

Return:

- what changed
- files changed
- tests run
- known limitations
- next recommended task

## 4. Context discipline

Do not feed every project file to the agent on every task. Start with `AGENTS.md`, then only the phase and files directly relevant to the current task.

## 5. Documentation synchronization

When a decision or contract changes:

- update the source-of-truth document
- add/update an ADR if the architectural decision changed
- update phase acceptance criteria if needed
