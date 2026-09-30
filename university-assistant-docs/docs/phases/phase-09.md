# Phase 09 — AI Assistant

## Objective
Implement grounded natural-language question answering.

## Tasks
- question router
- structured query service
- RAG retrieval service integration
- prompt builder
- LLM provider adapter
- answer formatter
- citation/source response
- insufficient-evidence behavior

## Acceptance criteria
- [ ] Structured questions use structured data.
- [ ] Regulation questions use RAG.
- [ ] Hybrid questions can combine both.
- [ ] No university-specific hallucination is returned when evidence is missing.
- [ ] Source information is returned when applicable.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Persian Retrieval Requirements

The retrieval pipeline must support Persian-language documents.

The system should account for:

- Persian character normalization
- Arabic/Persian character variants
- Persian punctuation
- نیم‌فاصله
- Persian and Latin numbers
- Common Persian word-form variations