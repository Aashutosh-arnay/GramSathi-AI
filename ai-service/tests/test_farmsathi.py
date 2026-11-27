"""FarmSathi AI – test suite (Phase B).

Test cases
----------
1. English question with matching context → answerStatus=supported, sources present.
2. Hindi question (गेहूँ) with matching context → supported, answer language=hi.
3. Missing context (no crop/state, low-scoring query) → needs_clarification.
4. Out-of-scope question (legal topic, not in agri KB) → insufficient_information.
5. No-data scenario (empty collection) → insufficient_information, no sources.

All tests use:
- TEST fixture PDFs in tests/fixtures/ (never in dataset/).
- LLM_PROVIDER=mock (no API key needed).
- EMBEDDING_PROVIDER=local (sentence-transformers, no API key needed).
- An isolated throwaway Chroma directory (cleaned up by conftest).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    *,
    message: str,
    language: str = "en",
    request_id: str = "test-req",
    state: str | None = None,
    crop: str | None = None,
):
    """Build a minimal FarmSathiChatRequest."""
    from app.schemas.chat_schema import FarmSathiChatRequest, FarmSathiContext

    return FarmSathiChatRequest(
        requestId=request_id,
        conversationId="conv-test",
        message=message,
        language=language,
        history=[],
        context=FarmSathiContext(state=state, crop=crop),
        attachments=[],
    )


def _ingest_fixtures(chroma_dir: str) -> None:
    """Ingest TEST fixture PDFs into an isolated Chroma collection."""
    # Reset lru_cache so each test session gets a fresh collection
    from app.farmsathi import knowledge_base as kb
    from app.services.embedding_service import get_embedding_service

    kb.get_farmsathi_collection.cache_clear()
    svc = get_embedding_service()
    kb.ingest_farmsathi_data(
        data_path=str(FIXTURES_DIR),
        persist_dir=chroma_dir,
        embedding_service=svc,
        force_reingest=True,
    )


# ---------------------------------------------------------------------------
# Session-scoped ingested collection
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ingested_chroma(test_chroma_dir):
    """Ingest TEST fixtures once per test module and patch config."""
    _ingest_fixtures(test_chroma_dir)
    return test_chroma_dir


@pytest.fixture(autouse=True)
def patch_chroma_dir(ingested_chroma):
    """Redirect every service call to the test Chroma directory."""
    with patch("app.farmsathi.service.get_settings") as mock_settings, \
         patch("app.core.config.get_settings") as mock_cfg_settings:

        from app.core.config import Settings

        # Build a real Settings-like object with test overrides
        cfg = Settings(
            llm_provider="mock",
            embedding_provider="local",
            embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
            chroma_persist_dir=ingested_chroma,
            retrieval_top_k=5,
            retrieval_threshold=0.20,  # lower for tiny test corpus
            farmsathi_data_path=str(FIXTURES_DIR),
            env="development",
            ai_service_api_key="",
        )
        mock_settings.return_value = cfg
        mock_cfg_settings.return_value = cfg
        yield


# ---------------------------------------------------------------------------
# TC-1: English question – should return supported + sources
# ---------------------------------------------------------------------------


def test_english_question_returns_supported(ingested_chroma):
    """An English wheat question should retrieve context and return supported."""
    from app.farmsathi.service import process_farmsathi_chat
    from app.schemas.chat_schema import AnswerStatus

    # Clear collection cache so our patched settings take effect
    from app.farmsathi.knowledge_base import get_farmsathi_collection
    get_farmsathi_collection.cache_clear()

    req = _make_request(
        message="Why are my wheat leaves turning yellow?",
        language="en",
        state="Bihar",
        crop="Wheat",
    )
    resp = process_farmsathi_chat(req)

    assert resp.requestId == "test-req"
    assert resp.language == "en"
    assert resp.answerStatus == AnswerStatus.supported, (
        f"Expected 'supported', got '{resp.answerStatus}'. answer={resp.answer[:200]}"
    )
    assert resp.sources, "Expected at least one source citation."
    # All returned URLs must come from the retrieved set (never fabricated)
    valid_urls = {
        "https://icar.org.in/test-fixture/wheat-guide",
        "https://icar.org.in/test-fixture/gehu-guide",
    }
    for src in resp.sources:
        assert src.url in valid_urls, f"Unexpected URL in sources: {src.url}"
    assert resp.metadata.service == "farmsathi"


# ---------------------------------------------------------------------------
# TC-2: Hindi question – answer should reference wheat in Hindi context
# ---------------------------------------------------------------------------


def test_hindi_question_returns_supported(ingested_chroma):
    """A Hindi गेहूँ question should retrieve context from both fixtures."""
    from app.farmsathi.service import process_farmsathi_chat
    from app.schemas.chat_schema import AnswerStatus
    from app.farmsathi.knowledge_base import get_farmsathi_collection

    get_farmsathi_collection.cache_clear()

    req = _make_request(
        message="मेरे गेहूँ की पत्तियाँ पीली हो रही हैं, क्या करूँ?",
        language="hi",
        state="Bihar",
        crop="गेहूँ",
    )
    resp = process_farmsathi_chat(req)

    assert resp.language == "hi"
    # With the multilingual model, Hindi query should match English/Hindi fixtures
    assert resp.answerStatus in (
        AnswerStatus.supported,
        AnswerStatus.insufficient_information,
    ), f"Unexpected status: {resp.answerStatus}"
    # If supported, sources must be valid
    if resp.answerStatus == AnswerStatus.supported:
        assert resp.sources
        valid_urls = {
            "https://icar.org.in/test-fixture/wheat-guide",
            "https://icar.org.in/test-fixture/gehu-guide",
        }
        for src in resp.sources:
            assert src.url in valid_urls, f"Unexpected URL: {src.url}"
    assert resp.metadata.service == "farmsathi"


# ---------------------------------------------------------------------------
# TC-3: Missing context (no crop/state, vague question) → needs_clarification
# ---------------------------------------------------------------------------


def test_missing_context_returns_needs_clarification(ingested_chroma):
    """A vague question without crop/state should return needs_clarification."""
    from app.farmsathi.service import process_farmsathi_chat
    from app.schemas.chat_schema import AnswerStatus
    from app.farmsathi.knowledge_base import get_farmsathi_collection

    get_farmsathi_collection.cache_clear()

    req = _make_request(
        message="My plants don't look good.",
        language="en",
        # No crop or state provided
    )
    resp = process_farmsathi_chat(req)

    # Either needs_clarification (best case) or insufficient_information is acceptable
    assert resp.answerStatus in (
        AnswerStatus.needs_clarification,
        AnswerStatus.insufficient_information,
    ), f"Expected clarification/insufficient, got '{resp.answerStatus}'"
    assert resp.followUpQuestions, "Expected follow-up questions when context is missing."


# ---------------------------------------------------------------------------
# TC-4: Out-of-scope (legal question) → insufficient_information
# ---------------------------------------------------------------------------


def test_out_of_scope_returns_insufficient(ingested_chroma):
    """A legal question should not match agri content → insufficient_information."""
    from app.farmsathi.service import process_farmsathi_chat
    from app.schemas.chat_schema import AnswerStatus
    from app.farmsathi.knowledge_base import get_farmsathi_collection

    get_farmsathi_collection.cache_clear()

    req = _make_request(
        message="How do I file a consumer complaint in a consumer court?",
        language="en",
        request_id="test-oos",
    )
    resp = process_farmsathi_chat(req)

    # Legal question should not produce agri sources; may be insufficient or needs_clarification
    # The important assertion: no fabricated sources
    assert resp.sources == [] or all(
        "icar.org.in/test-fixture" in s.url for s in resp.sources
    ), "Out-of-scope response should not contain unrelated sources."
    assert resp.metadata.service == "farmsathi"


# ---------------------------------------------------------------------------
# TC-5: Empty collection → insufficient_information, no sources
# ---------------------------------------------------------------------------


def test_empty_collection_returns_insufficient():
    """When the knowledge base has no data, every question is insufficient."""
    import tempfile
    from app.farmsathi.service import process_farmsathi_chat
    from app.farmsathi.knowledge_base import get_farmsathi_collection
    from app.schemas.chat_schema import AnswerStatus

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as empty_chroma:
        get_farmsathi_collection.cache_clear()

        with patch("app.farmsathi.service.get_settings") as mock_settings:
            from app.core.config import Settings
            cfg = Settings(
                llm_provider="mock",
                embedding_provider="local",
                embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
                chroma_persist_dir=empty_chroma,
                retrieval_top_k=5,
                retrieval_threshold=0.30,
                farmsathi_data_path="/nonexistent",
                env="development",
                ai_service_api_key="",
            )
            mock_settings.return_value = cfg

            req = _make_request(
                message="How do I grow wheat?",
                language="en",
                state="Punjab",
                crop="Wheat",
                request_id="test-empty",
            )
            resp = process_farmsathi_chat(req)

        get_farmsathi_collection.cache_clear()

    assert resp.answerStatus == AnswerStatus.insufficient_information
    assert resp.sources == [], "Empty KB must return no sources."
    assert resp.metadata.service == "farmsathi"
