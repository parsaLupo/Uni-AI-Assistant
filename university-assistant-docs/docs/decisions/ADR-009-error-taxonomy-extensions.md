# ADR-009 — Error taxonomy extensions

## Status

Accepted

## Decision

Implement the error envelope of `docs/04-api-specification.md` section 3 and
`docs/12-error-handling-observability.md` section 3 exactly, and add two codes to
the published list: `METHOD_NOT_ALLOWED` (HTTP 405) and `REQUEST_FAILED` (HTTP
400, generic malformed request fallback).

## Reasoning

The documented code list has no entry for a valid path called with an unsupported
HTTP method, and no fallback when a request fails validation without matching a
specific code. Without them, those cases would fall through to `INTERNAL_ERROR`
(500), which misreports a client mistake as a server fault and breaks the rule in
`docs/12-error-handling-observability.md` section 2 that clients can branch on
`error.code`. The frontend `ApiError` in `frontend/src/api/client.ts` mirrors the
same identifiers so both tiers branch on one vocabulary.

## Consequences

The code list is now a superset of the one printed in the specification, so the
specification page must be treated as amended by this ADR rather than as the
authoritative enumeration. Unhandled exceptions remain `INTERNAL_ERROR` with a
500 and are logged with the `X-Request-ID`; `docs/12` section 5 still requires
health to report `not_configured` as healthy, which `apps/common/views.py`
follows.
