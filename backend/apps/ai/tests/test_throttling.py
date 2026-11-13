"""Rate limits on the AI endpoints (docs/07-security.md section 4, Phase 15).

`ai_ask` is one shared per-user budget across `/ai/ask/` and
`/ai/ask/stream/`, so a caller cannot double its quota by switching endpoint.

Note on the rate fixture: DRF snapshots `DEFAULT_THROTTLE_RATES` onto
`SimpleRateThrottle.THROTTLE_RATES` when the throttling module is first
imported, so `override_settings(REST_FRAMEWORK=...)` does not reach the
throttle. Tests patch the class attribute directly instead (the suite clears
the locmem throttle cache between tests via the autouse conftest fixture).
"""

from __future__ import annotations

import pytest
from django.conf import settings

from apps.common.throttles import AiAskRateThrottle

pytestmark = pytest.mark.django_db

QUESTION = {"question": "شرایط مشروطی چیست؟"}


@pytest.fixture
def ai_rate(monkeypatch):
    """Set the effective `ai_ask` rate for the current test."""

    def _set(rate: str):
        rates = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "ai_ask": rate}
        monkeypatch.setattr(AiAskRateThrottle, "THROTTLE_RATES", rates, raising=False)

    return _set


def _client(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _user(email):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email=email, password="Str0ng-Passw0rd!"
    )


def test_ask_is_rate_limited_after_the_configured_budget(ai_rate):
    ai_rate("3/min")
    user = _user("ask-throttle@example.edu")
    client = _client(user)

    for _ in range(3):
        response = client.post("/api/v1/ai/ask/", QUESTION, format="json")
        assert response.status_code == 200

    throttled = client.post("/api/v1/ai/ask/", QUESTION, format="json")

    assert throttled.status_code == 429
    error = throttled.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert isinstance(error.get("retry_after_seconds", 0), (int, float))


def test_stream_shares_the_same_budget_as_ask(ai_rate):
    """One `ai_ask` budget covers both ask endpoints."""
    ai_rate("2/min")
    user = _user("stream-throttle@example.edu")
    client = _client(user)

    assert client.post("/api/v1/ai/ask/", QUESTION, format="json").status_code == 200
    stream = client.post("/api/v1/ai/ask/stream/", QUESTION, format="json")
    assert stream.status_code == 200

    throttled = client.post("/api/v1/ai/ask/", QUESTION, format="json")
    assert throttled.status_code == 429


def test_budget_is_per_user_not_per_ip(ai_rate):
    """Two users behind one address each get their own budget."""
    ai_rate("1/min")
    client_a = _client(_user("user-a@example.edu"))
    client_b = _client(_user("user-b@example.edu"))

    assert client_a.post("/api/v1/ai/ask/", QUESTION, format="json").status_code == 200
    throttled = client_a.post("/api/v1/ai/ask/", QUESTION, format="json")
    assert throttled.status_code == 429

    # The second user is unaffected by the first user's exhausted budget.
    assert client_b.post("/api/v1/ai/ask/", QUESTION, format="json").status_code == 200


def test_throttle_runs_before_the_provider_is_called(ai_rate):
    """A throttled request never reaches the answer service.

    The 429 response must use the error envelope, not an SSE/partial answer
    body, proving the check happens in DRF's initial() before the view body.
    """
    ai_rate("1/min")
    user = _user("early-throttle@example.edu")
    client = _client(user)
    assert client.post("/api/v1/ai/ask/", QUESTION, format="json").status_code == 200

    throttled = client.post("/api/v1/ai/ask/stream/", QUESTION, format="json")

    assert throttled.status_code == 429
    assert throttled.json()["error"]["code"] == "RATE_LIMITED"
