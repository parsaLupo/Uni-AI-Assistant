# Phase 11 — Course Selection Assistant

## Objective
Add deterministic eligibility checks and AI explanation.

## Rules
- passed prerequisite check
- availability in current term
- credit limit
- duplicate/passed course check
- schedule conflict
- other documented academic rules

## Critical architecture rule
The rules engine decides eligibility. The LLM explains the deterministic result.

## Acceptance criteria
- [x] Eligibility results are reproducible.
- [x] Each rejection has a machine-readable reason.
- [x] AI explanation does not override backend eligibility.

## Implementation record (completed 2026-11-09)

**Rules engine** — `backend/apps/students/course_selection.py`
(pure, DB-driven, `engine_version="phase11-rules-v1"`): the documented rules in
the exact order `UNKNOWN_COURSE` → `ALREADY_PASSED` → `ALREADY_PLANNED` →
`PREREQUISITE_MISSING` → `NOT_OFFERED_CURRENT_TERM` / `OFFERING_CLOSED` /
`SCHEDULE_CONFLICT` → `CREDIT_LIMIT_EXCEEDED`, each producing a
`SelectionReason(code, message, params)`; `SelectionDecision.to_dict()` /
`from_dict()` carry the full serialisable result including what-if credit
totals. Credit limit default 20 (OA-24,
`COURSE_SELECTION_MAX_TERM_CREDITS`). Schedule rule blocks only when *every*
open section conflicts; a conflict-free section is picked deterministically.

**Explanation layer** — `backend/apps/ai/selection_explanation.py`:
`SelectionExplanationService(provider).explain(decision)` →
`{"text", "source": "composed" | "llm", "engine_eligible"}`. The prompt
contains only the engine JSON plus "paraphrase, never change the verdict"
rules; any LLM output contradicting `decision.eligible` (lexical check on
normalized Persian, ZWNJ/Arabic-yeh variants included) or a failing provider
degrades to the deterministic composed text.

**API** — `POST /api/v1/students/me/course-selection/`
(`apps/students/views.py:CourseSelectionView`,
`docs/api/course-selection.md`): student-role gated, strict what-if extra-code
lookup (unknown extra → `400`), unknown course → `404`, empty code → `400`;
embedding the composed explanation in the response.

**UI** — `frontend/src/features/selection/` at `/selection`
(nav «انتخاب درس», `fact_check` icon): course-code + what-if form, verdict
badge, machine-readable reason chips, Persian-digits credit totals, and the
backend-provided explanation.

**Tests** — `{apps/students,apps/ai}/tests` (one test per rule + API
surface + the contradicting-LLM acceptance test) and
`frontend/src/test/selection-page.test.tsx`; backend **314 passed**
(268 → 314), frontend **48 passed**, `tsc --noEmit` clean. **Migrations: none**
(the engine reads existing tables only).

**Known limitations**
- Credit limit number is the OA-24 working default until the registrar
  confirms the official value.
- The HTTP surface serves the deterministic composed explanation; the
  LLM-verbalised path exists in `SelectionExplanationService` (tested) and is
  wired for reuse by the assistant pipeline.
- Capacity/enrollment seats are not part of the rules (no documented policy);
  every rule feeds from existing admin-managed tables.
- An "already planned" course that itself overlaps its own plan schedule also
  carries `SCHEDULE_CONFLICT` — `ALREADY_PLANNED` remains the primary reason.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.
