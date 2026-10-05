# ADR-015 — React Router for client-side routes and guards

## Status

Accepted (implemented in Phase 03)

## Decision

Use `react-router-dom` v7 for client-side routing, public/private route
configuration and the auth guard (`RequireAuth`) of `docs/20-ui-navigation.md`.

## Reasoning

Phase 03 requires "React auth state and protected routes" — a guard needs a router to
redirect unauthenticated visitors from `/dashboard` to `/login`. Deferring the router
until Phase 05 would mean writing throwaway navigation code first. `docs/02` §4.2
already assigns `/login` and `/register` to the `auth` feature slice for Phase 03/05,
and route declarations are the structural half of that contract.

## Consequences

One new frontend dependency (`react-router-dom`, installed in Phase 03 per this ADR,
per `AGENTS.md` rule 10). Protected routes are a **convenience, not a security
boundary** — `docs/02` §3 and `docs/05` §8 are explicit that the server stays
authoritative; every API call still carries a Bearer token and is checked by DRF.
Phase 05 inherits the routing foundation when it builds the layout shell and adds the
remaining route groups (student, admin).
