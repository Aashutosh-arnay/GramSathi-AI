"""API contract tests: error codes, state normalization, input limits, and logging."""
from __future__ import annotations

import logging
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.states import CANONICAL_STATES, normalize_state
from app.main import app
from app.services.llm_service import GeminiLLMService


# ---------------------------------------------------------------------------
# State normalization & /api/v1/meta/states
# ---------------------------------------------------------------------------


def test_normalize_state_variants():
    assert normalize_state("UP") == "Uttar Pradesh"
    assert normalize_state("mp") == "Madhya Pradesh"
    assert normalize_state("बिहार") == "Bihar"
    assert normalize_state("  tamil   nadu ") == "Tamil Nadu"
    assert normalize_state("Atlantis") is None
    assert normalize_state("") is None
    assert normalize_state(None) is None


def test_meta_states_endpoint():
    client = TestClient(app)
    r = client.get("/api/v1/meta/states")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 36
    assert len(data["states"]) == 36
    assert "Bihar" in data["states"]
    assert "Delhi" in data["states"]


def test_meta_states_requires_api_key_when_configured():
    from app.core.config import Settings

    with patch("app.core.security.get_settings") as mock_sec:
        mock_sec.return_value = Settings(ai_service_api_key="test-secret-key", env="development")
        client = TestClient(app)

        r_unauth = client.get("/api/v1/meta/states")
        assert r_unauth.status_code == 401
        assert r_unauth.json()["error"]["code"] == "UNAUTHORIZED"

        r_ok = client.get("/api/v1/meta/states", headers={"AI-Service-Api-Key": "test-secret-key"})
        assert r_ok.status_code == 200


# ---------------------------------------------------------------------------
# Input limits & §6.3 validation error format
# ---------------------------------------------------------------------------


def test_input_limits_and_validation_error_format():
    client = TestClient(app)

    # 1. message > 2000 chars -> 422 in §6.3 format with requestId
    r_long = client.post(
        "/api/v1/farmsathi/chat",
        json={
            "requestId": "req-val-1",
            "conversationId": "conv-1",
            "message": "x" * 2001,
            "language": "en",
        },
    )
    assert r_long.status_code == 422
    body = r_long.json()
    assert body["requestId"] == "req-val-1"
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["retryable"] is False

    # 2. Unsupported language -> 422
    r_lang = client.post(
        "/api/v1/nyayasathi/chat",
        json={
            "requestId": "req-val-2",
            "conversationId": "conv-1",
            "message": "Hello",
            "language": "fr",
        },
    )
    assert r_lang.status_code == 422
    assert r_lang.json()["requestId"] == "req-val-2"
    assert r_lang.json()["error"]["code"] == "VALIDATION_ERROR"

    # 3. Non-empty attachments -> 422 with clear message
    r_att = client.post(
        "/api/v1/farmsathi/chat",
        json={
            "requestId": "req-val-3",
            "conversationId": "conv-1",
            "message": "Check this photo",
            "language": "en",
            "attachments": ["leaf.jpg"],
        },
    )
    assert r_att.status_code == 422
    assert "not supported" in r_att.json()["error"]["message"].lower()

    # 4. History truncated to last 6 messages
    from app.schemas.chat_schema import FarmSathiChatRequest

    hist = [{"role": "user", "content": f"msg-{i}"} for i in range(10)]
    req = FarmSathiChatRequest(
        requestId="req-hist",
        conversationId="conv-1",
        message="How is wheat grown?",
        language="en",
        history=hist,
    )
    assert len(req.history) == 6
    assert [m.content for m in req.history] == [f"msg-{i}" for i in range(4, 10)]


# ---------------------------------------------------------------------------
# End-to-end 429 & 503 error codes through FastAPI endpoints
# ---------------------------------------------------------------------------


def test_end_to_end_429_and_503_from_gemini(ingested_chroma=None):
    from app.farmsathi.knowledge_base import get_farmsathi_collection
    from app.core.config import Settings

    # Use fixtures chroma via test_farmsathi fixture style or mock retrieval to return 1 chunk
    from app.services.retrieval_service import RetrievedChunk

    fake_chunks = [
        RetrievedChunk(
            text="Wheat is sown in November.",
            score=0.80,
            source_title="ICAR Wheat Guide",
            publisher="ICAR",
            url="https://icar.org.in/wheat",
        )
    ]

    def handler_429(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Quota exceeded"}})

    def handler_503(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "Service unavailable"})

    client = TestClient(app)
    payload = {
        "requestId": "req-err-test",
        "conversationId": "conv-1",
        "message": "When should wheat be sown?",
        "language": "en",
        "context": {"state": "Bihar", "crop": "Wheat"},
    }

    with patch("app.farmsathi.service.RetrievalService.search", return_value=fake_chunks):
        # 429 -> LLM_RATE_LIMITED
        svc_429 = GeminiLLMService(
            api_key="fake-key",
            model="gemini-2.0-flash",
            transport=httpx.MockTransport(handler_429),
            retry_backoff=0.0,
        )
        with patch("app.farmsathi.service.get_llm_service", return_value=svc_429):
            r429 = client.post("/api/v1/farmsathi/chat", json=payload)
        assert r429.status_code == 429
        assert r429.json() == {
            "requestId": "req-err-test",
            "error": {
                "code": "LLM_RATE_LIMITED",
                "message": "The language model rate limit or quota was exceeded. Please try again shortly.",
                "retryable": True,
            },
        }

        # 503 -> LLM_UNAVAILABLE
        svc_503 = GeminiLLMService(
            api_key="fake-key",
            model="gemini-2.0-flash",
            transport=httpx.MockTransport(handler_503),
            retry_backoff=0.0,
        )
        with patch("app.farmsathi.service.get_llm_service", return_value=svc_503):
            r503 = client.post("/api/v1/farmsathi/chat", json=payload)
        assert r503.status_code == 503
        assert r503.json()["error"]["code"] == "LLM_UNAVAILABLE"
        assert r503.json()["error"]["retryable"] is True


# ---------------------------------------------------------------------------
# Logging check: no message text, history, API keys, or headers logged
# ---------------------------------------------------------------------------


def test_logging_never_emits_message_history_or_secrets(caplog):
    from app.core.config import Settings

    secret_msg = "TOP_SECRET_USER_QUESTION_98765"
    secret_hist = "TOP_SECRET_HISTORY_54321"
    secret_key = "SUPER_SECRET_API_KEY_11111"

    with patch("app.core.security.get_settings") as mock_sec:
        mock_sec.return_value = Settings(ai_service_api_key=secret_key, env="development")
        client = TestClient(app)

        with caplog.at_level(logging.INFO):
            r = client.post(
                "/api/v1/farmsathi/chat",
                headers={"AI-Service-Api-Key": secret_key},
                json={
                    "requestId": "req-log-check",
                    "conversationId": "conv-log",
                    "message": secret_msg,
                    "language": "en",
                    "history": [{"role": "user", "content": secret_hist}],
                    "context": {"state": "UP", "crop": "Wheat"},
                },
            )
            assert r.status_code == 200

    all_logs = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "req-log-check" in all_logs
    assert "/api/v1/farmsathi/chat" in all_logs
    assert "latency_ms=" in all_logs
    assert secret_msg not in all_logs
    assert secret_hist not in all_logs
    assert secret_key not in all_logs
