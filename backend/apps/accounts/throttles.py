"""Rate limiting for the auth endpoints (OA-09 / ADR-014 decision 5).

`auth_ip` (10/min) covers login and register via DRF's ScopedRateThrottle,
which keys anonymous callers by IP. Refresh gets its own scope keyed by the
*verified* user id — keying on an unverified claim would let an attacker rotate
arbitrary ids to stay under the per-IP limit; unusable tokens fall back to IP.
"""

from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.tokens import REFRESH_COOKIE_NAME, verified_user_id


class RefreshRateThrottle(SimpleRateThrottle):
    throttle_scope = "auth_refresh"

    def __init__(self):
        # ScopedRateThrottle sets self.scope in allow_request; this throttle is
        # used directly, so it must be set before the rate is looked up.
        self.scope = self.throttle_scope
        super().__init__()

    def get_cache_key(self, request, view):
        user_id = verified_user_id(request.COOKIES.get(REFRESH_COOKIE_NAME))
        if user_id is not None:
            ident = f"user:{user_id}"
        else:
            ident = f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
