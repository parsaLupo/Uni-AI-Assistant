# Production/local-release backend image (Phase 16).
#
# The same image runs Gunicorn (web) and Celery (worker); the Compose service
# command selects which. Development uses docker-compose.dev.yml, which
# overrides the command with Django's runserver and mounts the source tree.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# psycopg uses binary wheels, so no build toolchain is required here (ADR-002).
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Non-root runtime (docs/07-security.md section 1: defence in depth). The media
# directory is created here so a fresh named volume inherits app ownership.
RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chmod +x /app/docker/entrypoint.sh \
    && mkdir -p /app/media/documents \
    && chown -R app:app /app

USER app

EXPOSE 8000

# The entrypoint validates DEPLOYMENT_MODE=release|local-demo before starting.
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "-c", "docker/gunicorn.conf.py"]
