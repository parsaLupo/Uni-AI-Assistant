"""Phase 14 load probe (docs/08 §6, docs/11 Performance).

A dependency-free load probe so the performance budget can be recorded on the
seeded development stack without installing k6. It drives N concurrent users
against authenticated endpoints and reports p50/p95/p99 latency per endpoint.

    python backend/loadtest/load_probe.py \
        --base http://localhost:8000 \
        --email student@semnan.local --password 'Demo-Passw0rd!' \
        --users 20 --seconds 15

Endpoints covered (seeded data):

* ``GET /api/v1/courses/``           — plain paginated read
* ``GET /api/v1/course-offerings/``  — joined read (term/course/offering)
* ``POST /api/v1/ai/ask/``           — full RAG path (router → retrieval →
  mock provider); measured separately because AI latency is its own budget
  (docs/11 Performance).

The k6 equivalent for machines with k6 installed lives next to this file
(``k6_load.js``); both drive the same endpoints with the same budget.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BUDGET_MS_NON_AI = 500  # docs/11: "responsive" for CRUD reads on seeded data
BUDGET_MS_AI = 2_000  # measured separately; mock provider, no external LLM

PROBE_ROUTES = [
    {"name": "GET /courses/", "method": "GET", "path": "/api/v1/courses/", "ai": False},
    {
        "name": "GET /course-offerings/",
        "method": "GET",
        "path": "/api/v1/course-offerings/",
        "ai": False,
    },
    {
        "name": "POST /ai/ask/",
        "method": "POST",
        "path": "/api/v1/ai/ask/",
        "ai": True,
        "body": {"question": "شرایط مشروطی چیست؟"},
    },
]


def _request(
    base: str, token: str, route: dict, timeout: float
) -> tuple[int, float]:
    url = base + route["path"]
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if route["method"] == "POST":
        body = json.dumps(route.get("body", {}), ensure_ascii=False).encode("utf-8")
        data = body
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=route["method"])
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            pass
        status = 200
    except urllib.error.HTTPError as exc:  # a 4xx still measures the server path
        status = exc.code
        exc.read()
    return status, (time.perf_counter() - started) * 1000.0


def login(base: str, email: str, password: str) -> str:
    body = json.dumps({"email": email, "password": password}).encode()
    request = urllib.request.Request(
        base + "/api/v1/auth/login/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode())
    token = payload.get("access") or payload.get("access_token")
    if not token:
        raise SystemExit("login response had no access token")
    return token


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(pct / 100 * len(sorted_values)) - 1))
    return sorted_values[index]


def probe_route(
    base: str, token: str, route: dict, users: int, seconds: int
) -> dict:
    latencies: list[float] = []
    statuses: dict[int, int] = {}
    errors: list[str] = []
    lock = threading.Lock()
    deadline = time.monotonic() + seconds

    def worker():
        local: list[float] = []
        local_statuses: dict[int, int] = {}
        local_errors: list[str] = []
        while time.monotonic() < deadline:
            try:
                status, ms = _request(base, token, route, timeout=30.0)
                local.append(ms)
                local_statuses[status] = local_statuses.get(status, 0) + 1
            except Exception as exc:  # noqa: BLE001
                local_errors.append(f"{type(exc).__name__}: {exc}")
        with lock:
            latencies.extend(local)
            for status, count in local_statuses.items():
                statuses[status] = statuses.get(status, 0) + count
            errors.extend(local_errors[:1])

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(users)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    ordered = sorted(latencies)
    result = {
        "route": route["name"],
        "method": route["method"],
        "requests": len(ordered),
        "errors": len(errors),
        "status_counts": {str(k): v for k, v in sorted(statuses.items())},
        "p50_ms": round(_percentile(ordered, 50), 1),
        "p95_ms": round(_percentile(ordered, 95), 1),
        "p99_ms": round(_percentile(ordered, 99), 1),
        "mean_ms": round(statistics.fmean(ordered), 1) if ordered else 0.0,
        "max_ms": round(ordered[-1], 1) if ordered else 0.0,
    }
    if ordered and seconds > 0:
        result["rps"] = round(len(ordered) / seconds, 2)
    result["budget_ms"] = BUDGET_MS_AI if route["ai"] else BUDGET_MS_NON_AI
    result["within_budget"] = result["p95_ms"] <= result["budget_ms"]
    if errors:
        result["error_sample"] = errors[0]
    return result


def run(args: argparse.Namespace) -> dict:
    token = login(args.base, args.email, args.password)
    results = []
    for route in PROBE_ROUTES:
        result = probe_route(args.base, token, route, args.users, args.seconds)
        results.append(result)
        print(
            f"{result['route']:<22} n={result['requests']:<5} "
            f"p50={result['p50_ms']}ms p95={result['p95_ms']}ms "
            f"p99={result['p99_ms']}ms rps={result.get('rps', 0)} "
            f"budget={result['budget_ms']}ms "
            f"{'OK' if result['within_budget'] else 'OVER BUDGET'}"
        )
    return {
        "base": args.base,
        "users": args.users,
        "seconds_per_route": args.seconds,
        "budget_non_ai_ms": BUDGET_MS_NON_AI,
        "budget_ai_ms": BUDGET_MS_AI,
        "results": results,
        "passed": all(result["within_budget"] for result in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--email", default="student@semnan.local")
    parser.add_argument("--password", default="Demo-Passw0rd!")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--report", default=None, help="Write a JSON report here.")
    args = parser.parse_args()

    report = run(args)
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"report written: {path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
