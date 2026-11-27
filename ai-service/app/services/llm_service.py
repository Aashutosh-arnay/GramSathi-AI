"""LLM service – provider abstraction.

Supported providers (selected via LLM_PROVIDER env var):

* ``mock`` (default): assembles an answer directly from retrieved chunk text.
  No API key or network call required.  Useful for development and CI.
* ``gemini``: calls the Google Gemini API (requires ``LLM_API_KEY``).
  Returns a stub-safe error when the key is absent.

Add more providers by registering them in ``_build_provider``.
"""
from __future__ import annotations

import logging
import textwrap
from functools import lru_cache
from typing import Protocol, runtime_checkable

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMService(Protocol):
    """Minimal interface every LLM backend must satisfy."""

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        language: str = "en",
    ) -> str:
        """Return a plain-text answer given *system_prompt* and *user_message*."""
        ...


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------


class MockLLMService:
    """Key-free mock that assembles a readable answer from retrieved chunks.

    Behaviour:
    * If chunks are present in ``user_message`` (delimited by ``---``), it
      extracts and re-formats them into a readable numbered list.
    * Always prepends a clear ``[MOCK LLM]`` banner so the stub is obvious
      in development logs and test assertions.
    * Never fabricates citations; sources come exclusively from chunk metadata.
    """

    _BANNER = "[MOCK LLM – no real model loaded]"

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        language: str = "en",
    ) -> str:
        logger.debug("MockLLMService.generate called (language=%s)", language)

        # Extract the CONTEXT block injected by the prompt builder
        context_text = ""
        if "CONTEXT:" in user_message:
            after_ctx = user_message.split("CONTEXT:", 1)[1]
            context_text = after_ctx.split("QUESTION:", 1)[0].strip()

        is_legal = "nyayasathi" in system_prompt.lower()

        if not context_text or context_text.lower() in ("(none)", ""):
            if language == "hi":
                advice = (
                    "कृपया किसी योग्य वकील या अपने नज़दीकी विधिक सेवा प्राधिकरण (NALSA / SLSA) से संपर्क करें।"
                    if is_legal
                    else "कृपया अधिक संदर्भ प्रदान करें या किसी KVK विशेषज्ञ से संपर्क करें।"
                )
                return (
                    f"{self._BANNER}\n\n"
                    f"माफ़ कीजिए, इस सवाल का जवाब देने के लिए पर्याप्त जानकारी उपलब्ध नहीं है। {advice}"
                )
            advice = (
                "Please consult a qualified advocate or your nearest Legal Services Authority (NALSA / SLSA)."
                if is_legal
                else "Please provide more context or contact your local Krishi Vigyan Kendra (KVK)."
            )
            return (
                f"{self._BANNER}\n\n"
                "I'm sorry, there is insufficient information in the knowledge base "
                f"to answer this question. {advice}"
            )

        # Build a human-readable answer from the retrieved context
        chunks = [c.strip() for c in context_text.split("---") if c.strip()]
        snippet = "\n\n".join(
            f"{i+1}. {textwrap.shorten(c, width=400, placeholder=' …')}"
            for i, c in enumerate(chunks[:3])
        )

        if language == "hi":
            closing = (
                "विस्तृत कानूनी सहायता के लिए किसी योग्य वकील या NALSA / राज्य विधिक सेवा प्राधिकरण से संपर्क करें।"
                if is_legal
                else "अधिक सटीक सलाह के लिए अपने नज़दीकी KVK या कृषि विशेषज्ञ से संपर्क करें।"
            )
            return (
                f"{self._BANNER}\n\n"
                f"आपके प्रश्न के आधार पर उपलब्ध जानकारी:\n\n{snippet}\n\n"
                f"{closing}"
            )
        closing = (
            "For specific legal representation, please consult a qualified advocate or contact NALSA / SLSA."
            if is_legal
            else "For precise advice, please consult your local Krishi Vigyan Kendra (KVK) or an agricultural expert."
        )
        return (
            f"{self._BANNER}\n\n"
            f"Based on the available knowledge base:\n\n{snippet}\n\n"
            f"{closing}"
        )


# ---------------------------------------------------------------------------
# Gemini provider stub
# ---------------------------------------------------------------------------


class GeminiLLMService:
    """Google Gemini REST API provider.

    Enable with:
        LLM_PROVIDER=gemini
        LLM_API_KEY=<your-key>
        LLM_MODEL=gemini-2.0-flash   # pin a specific model name

    Both ``LLM_API_KEY`` and ``LLM_MODEL`` are required (no alias default).
    """

    _ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        transport=None,
        timeout: float = 20.0,
        retry_backoff: float = 0.5,
    ) -> None:
        from app.core.exceptions import LLMConfigError

        if not api_key or not api_key.strip():
            raise LLMConfigError(
                "LLM_PROVIDER=gemini requires LLM_API_KEY to be configured."
            )
        if not model or not model.strip():
            raise LLMConfigError(
                "LLM_PROVIDER=gemini requires LLM_MODEL to be pinned to a specific model name."
            )

        self._api_key = api_key.strip()
        self._model_name = model.strip()
        self._transport = transport
        self._timeout = timeout
        self._retry_backoff = retry_backoff
        logger.info("GeminiLLMService initialised (model=%s).", self._model_name)

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        language: str = "en",
    ) -> str:
        import time

        import httpx

        from app.core.exceptions import (
            LLMConfigError,
            LLMRateLimitedError,
            LLMUnavailableError,
        )

        url = self._ENDPOINT.format(model=self._model_name)
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self._api_key,
        }

        client_kwargs: dict = {"timeout": self._timeout}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        last_exc: Exception | None = None
        for attempt in range(2):  # initial attempt + 1 retry on 5xx/timeout/network
            try:
                with httpx.Client(**client_kwargs) as client:
                    resp = client.post(url, json=payload, headers=headers)

                status = resp.status_code
                if status == 429:
                    raise LLMRateLimitedError()
                if status in (401, 403):
                    # Never include key material or raw auth headers in error messages
                    raise LLMConfigError(
                        "LLM provider authentication failed due to invalid configuration."
                    )
                if 500 <= status < 600:
                    last_exc = LLMUnavailableError()
                    if attempt == 0:
                        time.sleep(self._retry_backoff)
                        continue
                    raise last_exc
                if status >= 400:
                    raise LLMUnavailableError()

                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    raise LLMUnavailableError()
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts).strip()

            except (LLMRateLimitedError, LLMConfigError, LLMUnavailableError):
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(self._retry_backoff)
                    continue
                raise LLMUnavailableError() from exc
            except Exception as exc:
                raise LLMUnavailableError() from exc

        raise LLMUnavailableError() from last_exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Return a singleton LLM service selected by LLM_PROVIDER."""
    settings = get_settings()
    provider = (settings.llm_provider or "mock").lower()

    if provider == "mock":
        logger.info("LLM provider: mock (no API key required).")
        return MockLLMService()

    if provider == "gemini":
        logger.info("LLM provider: Gemini.")
        return GeminiLLMService(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER='{provider}'. Supported: 'mock', 'gemini'."
    )
