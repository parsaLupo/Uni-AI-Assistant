"""Rate limiting behaviour (OA-09 / ADR-014 decision 5)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.throttles import RefreshRateThrottle
from apps.accounts.tokens import REFRESH_COOKIE_NAME

pytestmark = pytest.mark.django_db


def test_login_is_rate_limited_after_the_configured_burst(api_client):
    """auth_ip = 10/min: the eleventh attempt from one IP is rejected."""
    url = "/api/v1/auth/login/"
    payload = {"email": "anyone@example.edu", "password": "wrong-password-1"}

    statuses = [api_client.post(url, payload, format="json").status_code for _ in range(10)]
    assert statuses == [401] * 10

    throttled = api_client.post(url, payload, format="json")

    assert throttled.status_code == 429
    error = throttled.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert isinstance(error.get("retry_after_seconds", 0), (int, float))


def test_refresh_throttle_key_uses_the_verified_user(student):
    request = APIRequestFactory().get("/")
    request.COOKIES[REFRESH_COOKIE_NAME] = str(RefreshToken.for_user(student))

    key = RefreshRateThrottle().get_cache_key(request, None)

    assert f"user:{student.id}" in key


def test_refresh_throttle_key_falls_back_to_ip_for_unusable_tokens():
    request = APIRequestFactory().get("/")
    request.COOKIES[REFRESH_COOKIE_NAME] = "not-a-jwt"

    key = RefreshRateThrottle().get_cache_key(request, None)

    assert "ip:" in key
    assert "user:" not in key
