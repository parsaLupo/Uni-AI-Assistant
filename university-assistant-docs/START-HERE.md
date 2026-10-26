# START HERE — AI Agent Entry Point

این فایل نقطه شروع اجرای پروژه است.

## Read first

1. `AGENTS.md`
2. `docs/00-project-overview.md`
3. `docs/01-requirements.md`
4. `docs/02-system-architecture.md`
5. `docs/03-database-design.md`
6. `docs/13-project-scope.md`

سپس فقط phase جاری را بخوان.

## Current phase

`PHASE_07` — (next).

Completed: `PHASE_00` (baseline), `PHASE_01` (architecture & API contract),
`PHASE_02` (environment verification), `PHASE_03` (authentication &
authorization), `PHASE_04` (core academic data), `PHASE_05` (React foundation —
Persian/RTL shell), `PHASE_06` (Academic User Experience) — each `DONE` with a
verification record in `docs/phases/phase-00.md` … `phase-06.md`.

## First objective

در Phase 00 هیچ Feature کاربردی نساز. فقط baseline پروژه، دامنه، تصمیمات معماری و ساختار repository را مشخص کن.

## Agent operating mode

- Do not guess missing business rules when the decision materially affects data or security.
- Prefer explicit documented assumptions.
- Do not implement future features early.
- Keep `main` runnable after every completed phase.
- Every phase must end with tests/verification and documentation status.

## Phase transition rule

A phase moves to `DONE` only if its acceptance criteria are satisfied. The next phase can then begin.

## Required final report per task

```text
Task:

Implemented:
- ...

Files changed:
- ...

Tests:
- ...

Migrations:
- ...

Acceptance criteria:
- [x] ...
- [ ] ...

Known limitations:
- ...

Recommended next task:
- ...
```
