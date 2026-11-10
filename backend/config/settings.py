"""Django settings baseline for the University Smart Assistant API.

Phase 00 freezes the implementation baseline only: project wiring, the
documented error contract, request correlation/logging and a health endpoint.
No academic feature, RAG path or UI is implemented here
(`docs/phases/phase-00.md` — Non-goals).

Environment variable names follow `docs/09-deployment.md` section 3 and the
repository `.env.example`.
"""

import sys
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

from config.environment import (
    BASE_DIR,
    database_config,
    env_bool,
    env_int,
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
    # Machine-readable API contract (ADR-012): generates and serves openapi.yaml.
    "drf_spectacular",
    "apps.common",
    "apps.accounts",
    "apps.conversations",
    # Phase 04 — core academic data (docs/02 section 4.1 entity→app map).
    "apps.analytics",
    "apps.academics",
    "apps.professors",
    "apps.courses",
    "apps.students",
    "apps.calendar",
    "apps.exams",
    "apps.announcements",
    "apps.notifications",
    "apps.documents",
    "apps.rag",
    "apps.ai",
]

# Custom user model (ADR-014). Set while no other feature model exists — Phase 03
# precedes Phase 04 deliberately, so no later migration has to rewrite user
# references (AUTH_USER_MODEL cannot change after feature models exist).
AUTH_USER_MODEL = "accounts.User"

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
# PostgreSQL + pgvector is the only supported database engine (ADR-002).
# DATABASE_URL must always be set; there is no SQLite fallback.
DATABASES = {"default": database_config()}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Persian-first (AGENTS.md "Language & Localization", docs/11 section "Language and
# Localization Requirements"): user-facing text, including DRF/Django validation
# messages, renders in Persian. Both Django and DRF ship an `fa` translation
# catalog, so this needs no extra dependency.
LANGUAGE_CODE = env_str("DJANGO_LANGUAGE_CODE") or "fa"
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
    # Bearer/JWT first (docs/05 section 3, ADR-014); session auth remains only
    # so the browsable API still works during development.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.auth.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.common.errors.handle_exception",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Rate limits (OA-09 / ADR-014): login+register per IP, refresh per user.
    "DEFAULT_THROTTLE_RATES": {
        "auth_ip": env_str("RATE_AUTH_IP", "10/min"),
        "auth_refresh": env_str("RATE_AUTH_REFRESH", "30/min"),
    },
}

# OpenAPI 3 contract (ADR-012). The generated file is committed as openapi.yaml
# at the repository root and drift-checked in CI, so a contract change cannot
# merge silently (AGENTS.md section 6).
SPECTACULAR_SETTINGS = {
    "TITLE": "University Smart Assistant API",
    "VERSION": "1.0.0",
    "DESCRIPTION": (
        "Versioned REST API under /api/v1/. Errors always use the envelope from "
        "docs/04-api-specification.md section 3; codes are listed in "
        "docs/12-error-handling-observability.md. Generated source of truth: "
        "ADR-012."
    ),
    "SERVE_PUBLIC": True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    # Several models expose a `status` field (offerings, enrollments, exams) —
    # name the enums explicitly so the contract gets stable, readable names
    # instead of generated hashes (drf-spectacular warning, Phase 04).
    "ENUM_NAME_OVERRIDES": {
        "OfferingStatusEnum": "apps.courses.models.OfferingStatus",
        "EnrollmentStatusEnum": "apps.students.models.EnrollmentStatus",
        "ExamStatusEnum": "apps.exams.models.ExamStatus",
        "AuditActionEnum": "apps.analytics.models.AuditAction",
    },
}

# Authentication (docs/05, ADR-014) ------------------------------------------
# Short-lived access token (frontend memory only) + refresh token in an HttpOnly
# cookie that rotates on every use. Lifetimes come from .env.example so the
# deployment contract matches docs/09 section 3.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 5)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 7)),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_CLAIM": "user_id",
}

# Cookie flags (docs/07 section 1, docs/05 section 3): secure automatically in
# production (DEBUG off), explicitly overridable. Used by the refresh cookie and
# mirrored for session/CSRF cookies.
COOKIE_SECURE = env_bool("COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SAMESITE = "Lax"

# Argon2id first (docs/07 section 2, ADR-014); older hashers stay registered so
# any previously stored hash can still be verified during login.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

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

# Celery / Redis (ADR-011) ---------------------------------------------------
CELERY_BROKER_URL = env_str("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env_str("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", "pytest" in sys.modules)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
DOCUMENT_STORAGE_ROOT = env_str("DOCUMENT_STORAGE_ROOT", str(BASE_DIR / "media"))


