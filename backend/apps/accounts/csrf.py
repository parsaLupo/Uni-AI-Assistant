"""Explicit double-submit CSRF enforcement (OA-23, ADR-014 decision 4).

DRF marks its views csrf_exempt and enforces CSRF only for session
authentication, so the cookie-based refresh/logout endpoints would otherwise be
unprotected. The check runs *inside* the view and raises DRF's PermissionDenied:
a middleware-level CSRF failure would render an HTML 403 instead of the JSON
error envelope required by docs/04 section 3.
"""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

logger = logging.getLogger("app.auth")

CSRF_FAILURE_MESSAGE = "توکن CSRF معتبر ارسال نشده است."


def enforce_double_submit_csrf(request: Request) -> None:
    """Require X-CSRFToken to match the csrftoken cookie.

    The SPA reads the cookie Django set at login and echoes it back in the
    header; an attacker's cross-site request can trigger the cookie but cannot
    read it, so the echo proves same-origin script control (OA-23).
    """
    cookie_token = request.COOKIES.get(settings.CSRF_COOKIE_NAME, "")
    header_token = request.headers.get("X-CSRFToken", "")

    if cookie_token and header_token and secrets.compare_digest(cookie_token, header_token):
        # Also honour Django's own view-level rules (e.g. referer checks for
        # non-HTTPS deployments) so behaviour matches the framework. Django 5.2
        # signature: process_view(request, callback, callback_args,
        # callback_kwargs).
        middleware = CsrfViewMiddleware(get_response=lambda req: None)
        try:
            middleware.process_view(request, None, (), {})
        except DjangoPermissionDenied as exc:
            _reject(request, str(exc))
        return

    _reject(request, "missing or mismatched X-CSRFToken")


def _reject(request: Request, reason: str) -> None:
    # The precise reason stays in the logs; clients only get the Persian
    # envelope message (no oracle for which half of the pair was wrong).
    logger.warning(
        "csrf_rejected",
        extra={"request_id": getattr(request, "request_id", "-"), "reason": reason},
    )
    raise PermissionDenied(CSRF_FAILURE_MESSAGE)
