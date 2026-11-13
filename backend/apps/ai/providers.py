"""LLM provider adapter (Phase 09).

The interface is deliberately provider-agnostic. ``MockLLMProvider`` is the only
implementation shipped in this phase; a real provider can be added later by
implementing the same ``LLMProvider`` protocol without changing callers.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    provider_name: str
    model_id: str

    def chat(self, prompt: str, *, timeout: float = 30.0, max_retries: int = 1) -> str:
        """Return a text completion for *prompt*."""

class ProviderError(RuntimeError):
    """Normalized provider failure with a safe, non-secret category."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


class MockLLMProvider:
    """Deterministic, dependency-free LLM provider used for tests and dev.

    It never performs network I/O and never claims to be a real model.
    Failure scenarios can be injected through constructor arguments.
    """

    provider_name = "mock"

    def __init__(
        self,
        *,
        model_id: str = "mock-llm-provider",
        response_text: str | None = None,
        fail_with: BaseException | type[BaseException] | None = None,
        malformed: bool = False,
        attempts_before_success: int = 0,
    ) -> None:
        self.model_id = model_id
        self.response_text = response_text
        self.fail_with = fail_with
        self.malformed = malformed
        self.attempts_before_success = attempts_before_success
        self.call_count = 0

    def chat(self, prompt: str, *, timeout: float = 30.0, max_retries: int = 1) -> str:
        self.call_count += 1
        if self.attempts_before_success and self.call_count <= self.attempts_before_success:
            if self.fail_with is not None:
                raise (
                    self.fail_with
                    if isinstance(self.fail_with, BaseException)
                    else self.fail_with()
                )
            raise TimeoutError("mock provider timeout")
        if self.fail_with is not None and self.attempts_before_success == 0:
            raise (
                self.fail_with
                if isinstance(self.fail_with, BaseException)
                else self.fail_with()
            )
        if self.malformed:
            return "   "  # empty after strip -> treated as malformed by callers
        if self.response_text is not None:
            return self.response_text
        # Deterministic, clearly-mocked answer derived from the prompt.
        return "پاسخ آزمایشی مدل mock: " + (prompt.splitlines()[-1] if prompt else "")

    def chat_stream(
        self, prompt: str, *, timeout: float = 30.0, max_retries: int = 1
    ) -> Iterator[str]:
        if self.fail_with is not None:
            raise (
                self.fail_with
                if isinstance(self.fail_with, BaseException)
                else self.fail_with()
            )
        yield self.chat(prompt, timeout=timeout, max_retries=max_retries)


class GroqLLMProvider:
    provider_name = "groq"

    def __init__(
        self,
        api_key: str,
        *,
        model_id: str = "llama-3.3-70b-versatile",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 30.0,
        max_retries: int = 2,
        circuit_failure_threshold: int = 3,
        circuit_recovery_seconds: float = 30.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Groq API key is required.")
        self.api_key = api_key.strip()
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.max_retries = max(0, int(max_retries))
        self.circuit_failure_threshold = max(1, int(circuit_failure_threshold))
        self.circuit_recovery_seconds = max(0.0, float(circuit_recovery_seconds))

        self.last_usage = None
        self.last_latency_ms = None
        self.last_error_category = None
        self.last_response_model = None
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0
        self.total_failures = 0

        self._circuit_failures = 0
        self._circuit_open_until = 0.0

    def _circuit_open(self) -> bool:
        now = time.monotonic()
        if self._circuit_open_until and now < self._circuit_open_until:
            return True
        if self._circuit_open_until and now >= self._circuit_open_until:
            self._circuit_failures = 0
            self._circuit_open_until = 0.0
        return False

    def _record_failure(self) -> None:
        self._circuit_failures += 1
        if self._circuit_failures >= self.circuit_failure_threshold:
            self._circuit_open_until = time.monotonic() + self.circuit_recovery_seconds

    def _categorize_http_status(self, status_code: int) -> str:
        if status_code == 429:
            return "rate_limit"
        if status_code in {401, 403}:
            return "authentication"
        if status_code == 404:
            return "not_found"
        if status_code in {408, 504}:
            return "timeout"
        if 500 <= status_code <= 599:
            return "server_error"
        return "http_error"

    def _retryable(self, category: str) -> bool:
        return category in {"timeout", "network", "rate_limit", "server_error"}
    def chat(self, prompt: str, *, timeout: float = 30.0, max_retries: int = 1) -> str:
        if self._circuit_open():
            self.last_error_category = "circuit_open"
            raise ProviderError("circuit_open", "Groq provider circuit breaker is open.")

        effective_timeout = self.timeout if timeout is None else float(timeout)
        retries = self.max_retries if max_retries is None else int(max_retries)
        retries = max(0, min(retries, 5))

        last_error: ProviderError | None = None
        for attempt in range(retries + 1):
            started = time.monotonic()
            try:
                content, usage, response_model = self._request(prompt, effective_timeout)
                self.last_latency_ms = int((time.monotonic() - started) * 1000)
                self.last_usage = usage
                self.last_response_model = response_model or self.model_id
                self.last_error_category = None
                self._circuit_failures = 0

                if usage:
                    self.total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
                    self.total_completion_tokens += int(usage.get("completion_tokens") or 0)
                self.total_requests += 1

                if not isinstance(content, str) or not content.strip():
                    raise ProviderError("malformed_response", "Groq returned an empty response.")
                return content.strip()
            except ProviderError as exc:
                self.last_latency_ms = int((time.monotonic() - started) * 1000)
                self.last_error_category = exc.category
                self.total_failures += 1
                self._record_failure()
                last_error = exc
                if not self._retryable(exc.category) or attempt >= retries:
                    raise
                self._backoff(attempt, exc)
            except Exception as exc:  # noqa: BLE001
                category = "timeout" if isinstance(exc, TimeoutError) else "network"
                self.last_latency_ms = int((time.monotonic() - started) * 1000)
                self.last_error_category = category
                self.total_failures += 1
                self._record_failure()
                last_error = ProviderError(category, "Groq request could not be completed.")
                if not self._retryable(category) or attempt >= retries:
                    raise last_error from exc
                self._backoff(attempt, last_error)

        if last_error is not None:
            raise last_error
        raise ProviderError("unknown", "Groq request could not be completed.")

    def _request(self, prompt: str, timeout: float) -> tuple[str, dict | None, str | None]:
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "UniversitySmartAssistant/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            category = self._categorize_http_status(exc.code)
            raise ProviderError(category, f"Groq request failed with HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            category = "timeout" if isinstance(exc.reason, TimeoutError) else "network"
            raise ProviderError(category, "Groq request could not be completed.") from exc
        except TimeoutError as exc:
            raise ProviderError("timeout", "Groq request timed out.") from exc

        try:
            parsed = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("malformed_response", "Groq returned invalid JSON.") from exc

        choices = parsed.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError("malformed_response", "Groq returned no choices.")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ProviderError("malformed_response", "Groq returned a non-text response.")

        usage_raw = parsed.get("usage")
        usage = None
        if isinstance(usage_raw, dict):
            usage = {
                "prompt_tokens": usage_raw.get("prompt_tokens"),
                "completion_tokens": usage_raw.get("completion_tokens"),
                "total_tokens": usage_raw.get("total_tokens"),
            }

        return content, usage, parsed.get("model")

    def chat_stream(
        self, prompt: str, *, timeout: float = 30.0, max_retries: int = 1
    ) -> Iterator[str]:
        if self._circuit_open():
            self.last_error_category = "circuit_open"
            raise ProviderError("circuit_open", "Groq provider circuit breaker is open.")

        effective_timeout = self.timeout if timeout is None else float(timeout)
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(
                {
                    "model": self.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                    "stream": True,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "UniversitySmartAssistant/1.0",
            },
            method="POST",
        )

        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=effective_timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        parsed = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = parsed.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        yield content
        except urllib.error.HTTPError as exc:
            category = self._categorize_http_status(exc.code)
            self.last_error_category = category
            raise ProviderError(category, f"Groq request failed with HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            category = "timeout" if isinstance(exc.reason, TimeoutError) else "network"
            self.last_error_category = category
            raise ProviderError(category, "Groq request could not be completed.") from exc
        except TimeoutError as exc:
            self.last_error_category = "timeout"
            raise ProviderError("timeout", "Groq request timed out.") from exc
        finally:
            self.last_latency_ms = int((time.monotonic() - started) * 1000)

    def _backoff(self, attempt: int, error: ProviderError) -> None:
        delay = min(1.0, 0.25 * (2 ** attempt))
        if error.category == "rate_limit":
            delay = min(1.0, max(delay, 0.5))
        time.sleep(delay)

    @property
    def usage_summary(self) -> dict[str, int | None]:
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "requests": self.total_requests,
            "failures": self.total_failures,
        }


def build_llm_provider_from_env() -> LLMProvider | None:
    provider_name = os.environ.get("AI_PROVIDER", "").strip().lower()
    if not provider_name or provider_name == "mock":
        model_id = os.environ.get("AI_MODEL", "").strip() or "mock-llm-provider"
        return MockLLMProvider(model_id=model_id)

    if provider_name == "groq":
        api_key = os.environ.get("AI_PROVIDER_API_KEY", "")
        if not api_key.strip():
            return None
        model_id = os.environ.get("AI_MODEL", "").strip() or "llama-3.3-70b-versatile"
        timeout = float(os.environ.get("AI_TIMEOUT_SECONDS", "") or 30.0)
        max_retries = int(os.environ.get("AI_MAX_RETRIES", "") or 2)
        return GroqLLMProvider(
            api_key=api_key,
            model_id=model_id,
            timeout=timeout,
            max_retries=max_retries,
        )

    raise ValueError(f"Unsupported AI_PROVIDER value: {provider_name!r}")


def get_llm_provider() -> LLMProvider | None:
    return build_llm_provider_from_env()


