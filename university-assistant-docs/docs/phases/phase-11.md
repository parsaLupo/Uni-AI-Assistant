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
- [ ] Eligibility results are reproducible.
- [ ] Each rejection has a machine-readable reason.
- [ ] AI explanation does not override backend eligibility.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.
