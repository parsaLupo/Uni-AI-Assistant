#!/bin/sh
# Container entrypoint for the production/local-demo backend and worker.
#
# Validates the release environment before any application process starts
# (Phase 16: "production/local-demo configuration must not silently use
# insecure defaults"), then execs the actual command so PID 1 is Gunicorn or
# Celery and stop signals are delivered directly.
set -eu

if [ "${DEPLOYMENT_MODE:-}" = "release" ] || [ "${DEPLOYMENT_MODE:-}" = "local-demo" ]; then
    python -m config.release_check
fi

exec "$@"
