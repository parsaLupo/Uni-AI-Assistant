"""Shared scoped rate limits (docs/07-security.md sections 2 and 4, Phase 15).

`auth_ip`/`auth_refresh` live in `apps.accounts.throttles` because they carry
auth-specific keying rules. AI ask and document upload use the generic
per-user key here: throttling by user id means one compromised account cannot
multiply its budget by rotating IPs, and anonymous callers (none are allowed
through on these endpoints anyway) fall back to the client IP.
"""

from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class UserScopedRateThrottle(SimpleRateThrottle):
    """Scoped rate limit keyed by the authenticated user id, IP fallback.

    Mirrors `apps.accounts.throttles.RefreshRateThrottle`: `self.scope` must be
    set before `super().__init__()` because the rate is looked up from
    `DEFAULT_THROTTLE_RATES[self.scope]` at construction time.
    """

    def __init__(self):
        self.scope = self.throttle_scope
        super().__init__()

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            ident = user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AiAskRateThrottle(UserScopedRateThrottle):
    """Per-user budget on `/ai/ask` and `/ai/ask/stream` (`RATE_AI_ASK`)."""

    throttle_scope = "ai_ask"


class UploadRateThrottle(UserScopedRateThrottle):
    """Per-admin budget on document upload (`RATE_UPLOAD`)."""

    throttle_scope = "upload"
