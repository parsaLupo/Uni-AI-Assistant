# Backend image for local development and, later, deployment.
# Python 3.13 matches the version pinned for Phase 00 verification.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg uses binary wheels, so no build toolchain is required here (ADR-002).
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Non-root container (docs/07-security.md section 1: defence in depth).
RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Overridden by docker-compose for the live-reload dev command.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
