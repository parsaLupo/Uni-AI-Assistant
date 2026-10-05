# ADR-012 — OpenAPI schema as the machine-checked API contract

## Status

Accepted (implemented in Phase 01)

## Decision

The API contract is an **OpenAPI 3.1 document generated from the Django code** with
`drf-spectacular` 0.30.0, served at `GET /api/v1/schema/`, and **committed at the
repository root as `openapi.yaml`**. CI fails when the schema is invalid or when the
committed file differs from the regenerated one. The frontend generates its typed
client from this file (ADR-013, Phase 05).

## Reasoning

`docs/04` is prose: over 17 phases, frontend/backend drift is inevitable and
undetectable. `AGENTS.md` §6 forbids silently changing API contracts, but prose
cannot enforce that — a committed schema makes **every** contract change a visible,
reviewable diff. Because the schema is generated from serializers and views, it
reflects what the code actually does rather than what a document once claimed, and
`docs/04` §6's catalog remains the human summary while `openapi.yaml` is the
machine-readable source of truth.

## Consequences

Any serializer, route or status change requires regenerating and committing
`openapi.yaml` (one documented command); CI enforces this, so an unreviewed contract
change cannot merge. Endpoints must carry schema metadata (serializer field
descriptions, `extend_schema`) for the document to be useful to humans as well as
machines. Authentication schemes appear in the schema once Phase 03 adds them. This
adds one runtime dependency (`drf-spectacular`, in `requirements.txt`), justified
here per `AGENTS.md` rule 10. Security-testing of the schema endpoint follows the
public-read rules of `/api/v1/health/`.
