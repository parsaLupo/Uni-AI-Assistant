# Gunicorn configuration (Phase 16 local-release deployment).
#
# The values are environment-tunable so the same image serves a laptop demo and
# a future single-host deployment without rebuilding. Gunicorn's gthread worker
# is used because the AI endpoints include a streaming (SSE) response: threads
# keep a long-lived stream from blocking unrelated requests.
import multiprocessing
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


# One worker per available core up to 4 by default; the local demo sets 3.
workers = _int("GUNICORN_WORKERS", max(2, min(4, (multiprocessing.cpu_count() or 2) // 2)))
threads = _int("GUNICORN_THREADS", 2)
worker_class = "gthread"
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
timeout = _int("GUNICORN_TIMEOUT", 120)
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int("GUNICORN_KEEPALIVE", 5)
# Recycle workers periodically: bounds any slow leak over a long demo session.
max_requests = _int("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _int("GUNICORN_MAX_REQUESTS_JITTER", 100)

# Container stdout/stderr is the structured log stream (docs/12).
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Only nginx can reach this container (no host port); trust its forwarded headers.
forwarded_allow_ips = "*"
proxy_allow_ips = "*"
