# ADR-011 — Background ingestion worker (Redis + Celery)

## Status

Accepted (recorded in Phase 01; implementation belongs to Phase 07)

## Decision

Document ingestion — extraction, cleaning, normalization, chunking, embedding and
indexing — runs in a **background worker** fed by a Redis queue (Celery). The HTTP
upload request only validates the file, stores it, creates the `Document` row and
enqueues a job; it responds `202 Accepted` with a status URL. Redis is also the
intended store for the rate limiting required by `docs/07` §2.

## Reasoning

`docs/06` §3 and Phase 07 describe the processing stages but imply they run inside
the request. On a real 50-page regulation PDF that is tens of seconds to minutes of
CPU time plus embedding-provider calls, which means request timeouts, a blocked
worker while it runs, and an API that degrades during exactly the operation admins
use most. `docs/09` §2 already anticipated "a background worker can be added later if
document ingestion becomes asynchronous" — for real PDFs it is asynchronous from day
one. Redis serves two separately documented requirements (async ingestion for
Phase 07, cross-process rate limits for Phases 03/15), so this introduces exactly one
new infrastructure dependency, required by the consuming phase and documented here as
`AGENTS.md` rule 10 demands.

## Consequences

`docker-compose.yml` gains `redis` and `worker` services in Phase 07; the documents
API exposes per-stage job status and retry (`pipeline.md` §2); idempotency is keyed
on the file checksum so re-enqueueing is safe. Until Phase 07 the application has no
background jobs and must not depend on Redis being present. Tests use an eager/in-memory
queue so the unit suite needs no Redis; CI may add a Redis service when the worker
lands.
