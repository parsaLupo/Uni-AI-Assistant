# Phase 10 — Conversations

## Objective
Create a persistent ChatGPT-like conversation experience.

## Tasks
- create/list/detail conversation APIs
- message creation
- history persistence
- delete/archive
- rename
- React chat UI
- source cards
- related question UI as a later enhancement

## Acceptance criteria
- [ ] Student can create a conversation.
- [ ] Messages persist.
- [ ] Only owner can read/delete own conversations.
- [ ] Assistant answers show sources when available.

## Agent execution contract

Before implementation, read `AGENTS.md` and all documents referenced by this phase. Do not start later phases unless explicitly instructed.

At completion, report changed files, tests run, migrations, acceptance criteria status, and known limitations.

## Language Requirements

- The assistant responds in Persian by default.
- Persian user queries must be supported.
- The system should preserve Persian terminology from official university sources.
- The assistant should avoid inventing Persian terminology when an official term exists.
- If the retrieved source is Persian, the response should normally use the same terminology.