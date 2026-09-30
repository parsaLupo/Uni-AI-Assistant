# ADR-007 — Monorepo layout

## Status

Accepted

## Decision

Keep one repository with `backend/` (Django), `frontend/` (React + Vite), a
root `docker-compose.yml`, a root `.env.example`, and the specification kept in
the versioned `university-assistant-docs/` directory that `AGENTS.md` requires
agents to read before coding.

## Reasoning

Phase 00 requires a single runnable baseline (`docs/02-system-architecture.md`
section 6 deployment topology, `docs/19-git-and-release.md` section 2 trunk
based flow). A monorepo lets one commit, one CI run, and one `docker compose up`
cover both tiers, and keeps the phase acceptance criteria and the code they
verify in the same review unit.

## Consequences

Two language toolchains live in one repo, so CI runs two independent jobs
(`backend`, `frontend`) with separate caches and no shared lockfile. Backend
imports must never reach into `frontend/` and vice versa; the only contract
between them is the versioned REST API described in `docs/04-api-specification.md`
and mirrored by `frontend/src/api/client.ts`.
