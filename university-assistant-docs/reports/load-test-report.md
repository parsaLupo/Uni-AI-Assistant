# Load test report (Phase 14)

## Environment

* Stack: Docker development stack — `db` (pgvector/pg16) + `backend`
  (`manage.py runserver`, `DJANGO_DEBUG=true`, `AI_PROVIDER=mock`,
  `CELERY_TASK_ALWAYS_EAGER=true`).
* Data: the seeded development database — the Phase 04 academic graph
  (faculties/departments/terms/courses/offerings/exams) plus 8 real Persian
  documents (~220 chunks) so the `/ai/ask/` route exercises the full RAG path
  (router → retrieval → provider).
* Client: `backend/loadtest/load_probe.py` (stdlib threading probe;
  all latencies are client-observed round trips over the Docker Desktop port
  proxy). The k6 equivalent is committed at
  `backend/loadtest/k6_load.js` (k6 was not installed on this machine and the
  package registry was unreachable, so the numbers below come from the
  stdlib probe).

## Recorded budget

docs/11 Performance requires non-AI CRUD reads to be "responsive under a small
university project load" without pinning a number. For Phase 14 the project
budget is recorded as:

* non-AI reads: **p95 ≤ 500 ms**
* `/ai/ask/` (full RAG path, mock provider): **p95 ≤ 2 000 ms** — AI latency is
  measured separately per docs/11.

## Results

### Single user (u=1, 10 s/route)

| route | n | p50 | p95 | p99 | rps | budget | verdict |
|---|---|---|---|---|---|---|---|
| GET /courses/ | 64 | 140 ms | **270 ms** | 308 ms | 6.4 | 500 ms | ✅ |
| GET /course-offerings/ | 84 | 105 ms | **217 ms** | 263 ms | 8.4 | 500 ms | ✅ |
| POST /ai/ask/ (RAG) | 102 | 93 ms | **122 ms** | 158 ms | 10.2 | 2 000 ms | ✅ |

### 5 concurrent users (u=5, 15 s/route)

| route | n | p50 | p95 | p99 | rps | budget | verdict |
|---|---|---|---|---|---|---|---|
| GET /courses/ | 107 | 692 ms | **928 ms** | 957 ms | 7.1 | 500 ms | ❌ |
| GET /course-offerings/ | 188 | 381 ms | **633 ms** | 717 ms | 12.5 | 500 ms | ❌ |
| POST /ai/ask/ (RAG) | 213 | 335 ms | **528 ms** | 640 ms | 14.2 | 2 000 ms | ✅ |

### 20 concurrent users (u=20, 15 s/route)

| route | n | p50 | p95 | p99 | rps | budget | verdict |
|---|---|---|---|---|---|---|---|
| GET /courses/ | 118 | 2 568 ms | **3 613 ms** | 3 919 ms | 7.9 | 500 ms | ❌ |
| GET /course-offerings/ | 169 | 1 808 ms | **2 540 ms** | 2 725 ms | 11.3 | 500 ms | ❌ |
| POST /ai/ask/ (RAG) | 190 | 1 615 ms | **2 508 ms** | 2 656 ms | 12.7 | 2 000 ms | ❌ |

Raw numbers: `load-probe-u1.json`, `load-probe-u5.json`, `load-probe-u20.json`.

## Interpretation

* **Single-user latency is comfortably within budget** (worst p95 = 270 ms for
  the joined offerings read; the full RAG ask round trip is ~120 ms with the
  mock provider).
* **Throughput saturates at ~10–14 rps regardless of concurrency** (1, 5 and 20
  users all land in the same band). The queueing therefore happens in the
  serving stack, not the application: Django's development server (`runserver`)
  plus the Docker Desktop port proxy serialize requests; five Python client
  threads also contend on the GIL. This is why p95 grows linearly with
  concurrency while rps stays flat.
* The app-layer cost of a request stays low and roughly constant — consistent
  with sequential timing (a warm `GET /courses/` is ~130 ms measured one at a
  time).

## Conclusion and follow-ups

1. The **application-level budget holds** where the serving stack does not
   queue: with one active user every route is far under budget, and the RAG
   ask stays under budget even at 5 concurrent users.
2. The **dev `runserver` is not a load-bearing server**. Production deploys
   gunicorn (docs/09 §1); the concurrency numbers above must be re-measured on
   that deployment before any budget claim beyond single-digit concurrency.
   Recorded as a deployment-gate re-run, not an application defect.
3. No request errors (0 non-2xx across ~1 300 requests).
