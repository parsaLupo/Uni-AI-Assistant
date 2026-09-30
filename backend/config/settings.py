"""Django settings baseline for the University Smart Assistant API.

Phase 00 freezes the implementation baseline only: project wiring, the
documented error contract, request correlation/logging and a health endpoint.
No academic feature, RAG path or UI is implemented here
(`docs/phases/phase-00.md` — Non-goals).

Environment variable names follow `docs/09-deployment.md` section 3 and the
repository `.env.example`.
"""

import sys

from django.core.exceptions import ImproperlyConfigured

from config.environment import (
    BASE_DIR,
    database_config,
    env_bool,
    env_list,
    env_str,
)

# Development-only fallback so `manage.py` and the test suite work without a
# committed secret (AGENTS.md section 9: never commit secrets). Running with
# DEBUG=False refuses to boot without an explicit key.
DEV_SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"

DEBUG = env_bool("DJANGO_DEBUG", False)
IS_TESTS = "pytest" in sys.modules

SECRET_KEY = env_str("DJANGO_SECRET_KEY") or (DEV_SECRET_KEY if (DEBUG or IS_TESTS) else "")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is required when DJANGO_DEBUG is false "
        "(docs/07-security.md section 1). Copy .env.example to .env, or set "
        "DJANGO_SECRET_KEY in the process environment."
    )

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    ("localhost", "127.0.0.1", "0.0.0.0", "testserver") if (DEBUG or IS_TESTS) else (),
)
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be set explicitly outside development (docs/07-security.md section 1)."
    )

# Application definition -----------------------------------------------------
# `apps.common` is the only implemented app in Phase 00. The other directories
# under backend/apps/ are structural placeholders documented in
# docs/02-system-architecture.md section 4.
#
# django.contrib.admin is intentionally not enabled: the MVP admin surface is
# specified as REST endpoints under /api/v1/admin/
# (docs/04-api-specification.md section 6), so enabling the Django admin UI now
# would add an unreviewed permission surface.
# See docs/21-open-assumptions.md.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.common",
]

MIDDLEWARE = [
    # First, so every log line and the response header carry the correlation
    # id (docs/12-error-handling-observability.md section 4).
    "apps.common.middleware.RequestContextMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database ------------------------------------------------------------------
# PostgreSQL + pgvector is the target engine (ADR-002). SQLite is used only
# when DATABASE_URL is absent, so the baseline is verifiable without Docker.
DATABASES = {"default": database_config()}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# CORS ----------------------------------------------------------------------
# The refresh token will travel in an HttpOnly cookie
# (docs/05-authentication.md section 3), so credentialed cross-origin requests
# must be allowed — but only for explicitly configured origins.
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ("http://localhost:5173", "http://127.0.0.1:5173") if DEBUG else (),
)

# Django REST Framework -----------------------------------------------------
# Secure-by-default permissions: every future endpoint is authenticated unless
# it explicitly opts out (as the health endpoint does). The pagination class
# fixes the list-response shape that docs/04-api-specification.md section 4
# requires to stay consistent across the API.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.common.errors.handle_exception",
}

# Observability -------------------------------------------------------------
# Request logs carry request id, method, path, status and latency
# (docs/12-error-handling-observability.md section 3). The values are attached
# by apps.common.middleware.RequestContextMiddleware and the filter guarantees
# the keys exist for log lines emitted outside a request.
# Raw credentials and tokens are never logged (AGENTS.md section 9).
LOG_LEVEL = env_str("DJANGO_LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {
            "()": "apps.common.middleware.RequestContextFilter",
        },
    },
    "formatters": {
        "standard": {
            "format": (
                "%(asctime)s level=%(levelname)s request_id=%(request_id)s "
                "logger=%(name)s msg=%(message)s"
            ),
        },
        "access": {
            "format": (
                "%(asctime)s level=%(levelname)s request_id=%(request_id)s "
                "method=%(method)s path=%(path)s status=%(status_code)s "
                "latency_ms=%(latency_ms)s msg=%(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["request_context"],
        },
        "access_console": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "filters": ["request_context"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "app.access": {
            "handlers": ["access_console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "app.errors": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


