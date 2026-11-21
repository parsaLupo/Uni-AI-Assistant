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

`PHASE_16` — Local Production-Ready Release & Demo Deployment — **DONE**.

Completed: `PHASE_00` … `PHASE_16`, each with a verification record in
`docs/phases/phase-00.md` … `phase-16.md`.

Phase 16 is the final phase in the current scope. No later phase has been
started. The deployment runbook is [`../DEPLOYMENT.md`](../DEPLOYMENT.md).

## First objective

Phase 16 فقط برای آماده‌سازی انتشار محلی، دموی دانشگاهی، پشتیبان‌گیری و
بازیابی است. استقرار عمومی/VPS، دامنه و HTTPS خارج از دامنه این فاز هستند.

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
