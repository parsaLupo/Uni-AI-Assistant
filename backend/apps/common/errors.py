"""Project error contract.

`docs/04-api-specification.md` section 3 fixes the error envelope and
`docs/12-error-handling-observability.md` section 1 fixes the machine-readable
codes. They are implemented once, here, so every DRF endpoint — present and
future — returns a single shape.

Internal failures are logged with the correlation id but never serialized to
the client (AGENTS.md section 9, docs/09-deployment.md section 7).
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("app.errors")

# Codes from docs/12-error-handling-observability.md section 1.
VALIDATION_ERROR = "VALIDATION_ERROR"
AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
PERMISSION_DENIED = "PERMISSION_DENIED"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
RATE_LIMITED = "RATE_LIMITED"
AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
DOCUMENT_PROCESSING_ERROR = "DOCUMENT_PROCESSING_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Extensions to the taxonomy above, approved in ADR-008 because the base list
# has no code for these two situations.
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
REQUEST_FAILED = "REQUEST_FAILED"


class ApiError(APIException):
    """Raise to return a documented error envelope with an explicit code."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = VALIDATION_ERROR
    default_message = "The request could not be completed."

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.code = code
        self.message = message
        self.status_code = http_status or self.status_code
        self.details = details or {}


def build_error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    """Return the single error shape every endpoint must produce."""
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _code_for_status(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: VALIDATION_ERROR,
        status.HTTP_401_UNAUTHORIZED: AUTHENTICATION_REQUIRED,
        status.HTTP_403_FORBIDDEN: PERMISSION_DENIED,
        status.HTTP_404_NOT_FOUND: NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED: METHOD_NOT_ALLOWED,
        status.HTTP_409_CONFLICT: CONFLICT,
        status.HTTP_429_TOO_MANY_REQUESTS: RATE_LIMITED,
    }
    if status_code in mapping:
        return mapping[status_code]
    if status_code >= 500:
        return INTERNAL_ERROR
    return REQUEST_FAILED


def _message_from_detail(detail: Any, fallback: str) -> str:
    return detail if isinstance(detail, str) else fallback


def _details_from_detail(detail: Any) -> dict[str, Any]:
    if isinstance(detail, dict):
        return detail
    if isinstance(detail, (list, tuple)):
        return {"errors": list(detail)}
    if isinstance(detail, str):
        return {}
    return {"detail": str(detail)}


def _translate(exc: APIException, handled: Response) -> tuple[str, str, dict[str, Any], int]:
    """Map a DRF-handled exception onto (code, message, details, status)."""
    status_code = handled.status_code

    if isinstance(exc, ApiError):
        return exc.code, exc.message, exc.details, exc.status_code
    if isinstance(exc, ValidationError):
        return (
            VALIDATION_ERROR,
            "One or more fields are invalid.",
            _details_from_detail(exc.detail),
            status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return (
            AUTHENTICATION_REQUIRED,
            "Authentication credentials were not provided or are invalid.",
            {},
            status_code,
        )
    if isinstance(exc, PermissionDenied):
        message = _message_from_detail(exc.detail, "Access denied.")
        return PERMISSION_DENIED, message, {}, status_code
    if isinstance(exc, (NotFound, Http404)):
        message = _message_from_detail(exc.detail, "Resource not found.")
        return NOT_FOUND, message, {}, status_code
    if isinstance(exc, MethodNotAllowed):
        message = "HTTP method not allowed for this endpoint."
        return METHOD_NOT_ALLOWED, message, {}, status_code
    if isinstance(exc, Throttled):
        details = {"retry_after_seconds": exc.wait} if exc.wait else {}
        return RATE_LIMITED, "Too many requests. Please retry later.", details, status_code

    code = _code_for_status(status_code)
    fallback = _message_from_detail(exc.detail, "The request could not be completed.")
    return code, fallback, _details_from_detail(exc.detail), status_code


def handle_exception(exc: Exception, context: dict | None = None) -> Response | None:
    """DRF EXCEPTION_HANDLER producing the documented envelope for all errors."""
    handled = drf_exception_handler(exc, context)

    if handled is not None:
        code, message, details, status_code = _translate(exc, handled)
        handled.data = build_error_payload(code, message, details)
        handled.status_code = status_code
        return handled

    # Django exceptions DRF's default handler does not convert.
    if isinstance(exc, Http404):
        return Response(
            build_error_payload(NOT_FOUND, "Resource not found."),
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, DjangoPermissionDenied):
        return Response(
            build_error_payload(PERMISSION_DENIED, "Access denied."),
            status=status.HTTP_403_FORBIDDEN,
        )

    if settings.DEBUG:
        # Let Django render the technical error page for developers.
        return None

    request = (context or {}).get("request")
    logger.exception(
        "unhandled_exception",
        extra={
            "request_id": getattr(request, "request_id", "-"),
            "path": getattr(request, "path", "-"),
        },
    )
    message = "An unexpected error occurred. Please try again later."
    return Response(
        build_error_payload(INTERNAL_ERROR, message),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

