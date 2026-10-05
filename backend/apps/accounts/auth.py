"""JWT authentication wrapper guaranteeing envelope-consistent failures.

simplejwt signals some failure modes with its own TokenError, which DRF would
not convert — producing a 500 INTERNAL_ERROR for a merely expired token. Every
failure must surface as the documented 401 AUTHENTICATION_REQUIRED envelope
(docs/12 section 1), so token errors are normalized here (the handler already
suppresses the underlying English detail for AuthenticationFailed).
"""

from __future__ import annotations

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication as SimpleJWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Render the project authenticator as a Bearer JWT scheme in the contract."""

    target_class = "apps.accounts.auth.JWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):  # noqa: ARG002
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }


class JWTAuthentication(SimpleJWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except TokenError as exc:
            raise AuthenticationFailed(str(exc)) from exc
