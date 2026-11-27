"""Tests for GeminiLLMService error mapping, retry/backoff, and config checks.

Uses httpx.MockTransport so no real network calls are made.
"""
from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import (
    LLMConfigError,
    LLMRateLimitedError,
    LLMUnavailableError,
)
from app.services.llm_service import GeminiLLMService


def test_gemini_requires_api_key_and_pinned_model():
    with pytest.raises(LLMConfigError):
        GeminiLLMService(api_key="", model="gemini-2.0-flash")

    with pytest.raises(LLMConfigError):
        GeminiLLMService(api_key="fake-key", model="")


def test_gemini_429_maps_to_rate_limited():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Quota exceeded"}})

    svc = GeminiLLMService(
        api_key="fake-key",
        model="gemini-2.0-flash",
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    )
    with pytest.raises(LLMRateLimitedError) as exc_info:
        svc.generate("sys", "hi")

    assert exc_info.value.http_status == 429
    assert exc_info.value.code == "LLM_RATE_LIMITED"
    assert exc_info.value.retryable is True


@pytest.mark.parametrize("status_code", [401, 403])
def test_gemini_auth_error_maps_to_config_error_without_key_leak(status_code: int):
    secret = "super-secret-api-key-12345"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"error": {"message": f"Invalid key {secret}"}},
        )

    svc = GeminiLLMService(
        api_key=secret,
        model="gemini-2.0-flash",
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    )
    with pytest.raises(LLMConfigError) as exc_info:
        svc.generate("sys", "hi")

    assert exc_info.value.http_status == 500
    assert exc_info.value.code == "LLM_CONFIG_ERROR"
    assert exc_info.value.retryable is False
    assert secret not in exc_info.value.message


def test_gemini_5xx_retries_once_then_maps_to_unavailable():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"error": "upstream down"})

    svc = GeminiLLMService(
        api_key="fake-key",
        model="gemini-2.0-flash",
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    )
    with pytest.raises(LLMUnavailableError) as exc_info:
        svc.generate("sys", "hi")

    assert calls == 2
    assert exc_info.value.http_status == 503
    assert exc_info.value.code == "LLM_UNAVAILABLE"
    assert exc_info.value.retryable is True


def test_gemini_timeout_retries_once_then_succeeds():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("timed out")
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Recovered answer"}]}}]},
        )

    svc = GeminiLLMService(
        api_key="fake-key",
        model="gemini-2.0-flash",
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    )
    out = svc.generate("sys", "hi")
    assert calls == 2
    assert out == "Recovered answer"


def test_gemini_timeout_exhausts_retry_and_raises_unavailable():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("connect timed out")

    svc = GeminiLLMService(
        api_key="fake-key",
        model="gemini-2.0-flash",
        transport=httpx.MockTransport(handler),
        retry_backoff=0.0,
    )
    with pytest.raises(LLMUnavailableError) as exc_info:
        svc.generate("sys", "hi")

    assert calls == 2
    assert exc_info.value.http_status == 503
    assert exc_info.value.code == "LLM_UNAVAILABLE"
    assert exc_info.value.retryable is True
