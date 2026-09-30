# Phase 08 — RAG Ingestion and Retrieval

## Objective
Turn approved university documents into searchable semantic evidence.

## Tasks
- text extraction
- cleaning
- page-aware chunking
- metadata extraction/storage
- embedding generation
- pgvector storage
- similarity retrieval
- retrieval filters by document status/effective period

## Acceptance criteria
- [ ] Approved document becomes searchable.
- [ ] Retrieval returns relevant chunks for seeded test questions.
- [ ] Inactive/invalid document versions are excluded.
- [ ] Source metadata can be traced back to page/document.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.
