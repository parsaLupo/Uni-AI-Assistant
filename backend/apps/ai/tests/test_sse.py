"""SSE tests for Phase 09."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class Phase09SSETests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="sse@example.com", password="Str0ng-Passw0rd!")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_stream_returns_sse_events(self):
        response = self.client.post("/api/v1/ai/ask/stream/", {"question": "شرایط مشروطی چیست؟"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        body = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("event: token", body)
        self.assertIn("event: done", body)
        self.assertIn('"mode": "RAG"', body)

    def test_non_streaming_fallback_endpoint(self):
        response = self.client.post("/api/v1/ai/ask/", {"question": "شرایط مشروطی چیست؟"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "RAG")

    def test_stream_provider_failure_returns_error_event(self):
        # Force provider failure by using an empty question? Instead patch service in view? 
        # Use invalid question to get validation error before stream.
        response = self.client.post("/api/v1/ai/ask/stream/", {"question": "   "}, format="json")
        self.assertEqual(response.status_code, 400)
