# ADR-013 — Frontend server-state layer (TanStack Query)

## Status

Accepted (recorded in Phase 01; implementation belongs to Phase 05)

## Decision

All server state in React is managed with **TanStack Query** (`@tanstack/react-query`)
through hooks that wrap the API client generated from `openapi.yaml`. Components never
call `fetch` directly. One `QueryClient` provider owns the policy: retries, request
cancellation, cache invalidation, and mapping `error.code` to Persian text through
`src/i18n/fa.ts`. Forms use `react-hook-form` as a companion decision.

## Reasoning

Phases 06 and 10 produce ten-plus screens over server state. Hand-rolled
`useEffect` fetching is where loading/staleness/race-condition bugs come from, and
`docs/02` (frontend responsibilities) plus `docs/11` (Persian validation and error
messages) require *consistent* loading/empty/error handling everywhere — one data
layer makes that the default instead of per-page discipline. Recorded now because
`AGENTS.md` rule 10 requires a dependency to be documented before the phase that
needs it, and Phase 05 is where the shell is built.

## Consequences

The package is installed in Phase 05, not before, so the baseline keeps no unused
dependency. Query keys are centralized per resource so cache invalidation after
mutations (rename, publish, upload) is declarative. Optimistic updates are available
for safe actions (rename, mark-as-read). No SSR/streaming concern exists because the
app is a pure SPA. Test doubles come from MSW against the committed OpenAPI contract,
which keeps component tests honest about the API shape.
