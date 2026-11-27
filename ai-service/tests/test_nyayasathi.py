"""NyayaSathi AI – test suite (Phase C).

Test cases
----------
1. English question (consumer complaint) → supported, verified source, disclaimer.
2. Hindi question (मुफ्त कानूनी सहायता / NALSA) → Hindi disclaimer, valid status.
3. State-specific law (Bihar) → returns Bihar source, never Maharashtra.
4. State-specific law (Maharashtra) → returns Maharashtra source, never Bihar.
5. Missing state for state-specific question → needs_clarification + disclaimer.
6. No-sources case (empty collection) → insufficient_information + disclaimer.
7. Out-of-scope question (farming/cooking) → insufficient_information + disclaimer.
8. Hallucination trap (made-up Section 999Z) → does NOT confirm, + disclaimer.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

NYAYA_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "nyayasathi"


def _make_request(
    *,
    message: str,
    language: str = "en",
    request_id: str = "nyaya-req",
    state: str | None = None,
    category: str | None = None,
):
    from app.schemas.chat_schema import NyayaSathiChatRequest, NyayaSathiContext

    return NyayaSathiChatRequest(
        requestId=request_id,
        conversationId="conv-nyaya-test",
        message=message,
        language=language,
        history=[],
        context=NyayaSathiContext(country="India", state=state, category=category),
        attachments=[],
    )


@pytest.fixture(scope="module")
def ingested_nyaya_chroma(test_chroma_dir):
    """Ingest NyayaSathi TEST fixtures once per test module."""
    from app.nyayasathi import knowledge_base as kb
    from app.services.embedding_service import get_embedding_service

    kb.get_nyayasathi_collection.cache_clear()
    svc = get_embedding_service()
    kb.ingest_nyayasathi_data(
        data_path=str(NYAYA_FIXTURES_DIR),
        persist_dir=test_chroma_dir,
        embedding_service=svc,
        force_reingest=True,
    )
    return test_chroma_dir


@pytest.fixture(autouse=True)
def patch_nyaya_settings(ingested_nyaya_chroma):
    """Redirect NyayaSathi service calls to the test Chroma directory."""
    with patch("app.nyayasathi.service.get_settings") as mock_settings, \
         patch("app.core.config.get_settings") as mock_cfg:
        from app.core.config import Settings

        cfg = Settings(
            llm_provider="mock",
            embedding_provider="local",
            embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
            chroma_persist_dir=ingested_nyaya_chroma,
            retrieval_top_k=5,
            retrieval_threshold=0.20,
            nyayasathi_data_path=str(NYAYA_FIXTURES_DIR),
            env="development",
            ai_service_api_key="",
        )
        mock_settings.return_value = cfg
        mock_cfg.return_value = cfg
        yield


# ---------------------------------------------------------------------------
# TC-1: English question (Consumer Protection Act)
# ---------------------------------------------------------------------------


def test_english_consumer_question_supported():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    req = _make_request(
        message="How can I file a consumer complaint for defective goods?",
        language="en",
        state="Bihar",
        category="Consumer Rights",
    )
    resp = process_nyayasathi_chat(req)

    assert resp.answerStatus == AnswerStatus.supported
    assert resp.sources
    assert any("indiacode.nic.in/test-fixture/consumer-protection-2019" in s.url for s in resp.sources)
    assert "2020-07-20" in resp.answer
    assert resp.disclaimer and "Disclaimer" in resp.disclaimer
    assert resp.metadata.service == "nyayasathi"


# ---------------------------------------------------------------------------
# TC-2: Hindi question (मुफ्त कानूनी सहायता / NALSA)
# ---------------------------------------------------------------------------


def test_hindi_legal_aid_question():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    req = _make_request(
        message="मुझे मुफ्त कानूनी सहायता कहां से मिल सकती है?",
        language="hi",
        state="Bihar",
    )
    resp = process_nyayasathi_chat(req)

    assert resp.language == "hi"
    assert resp.answerStatus == AnswerStatus.supported
    assert resp.sources
    assert any("nalsa.gov.in/test-fixture/legal-aid-section-12" in s.url for s in resp.sources)
    assert resp.disclaimer and "अस्वीकरण" in resp.disclaimer
    assert resp.metadata.service == "nyayasathi"


# ---------------------------------------------------------------------------
# TC-3 & TC-4: State-specific law (matching state vs different state)
# ---------------------------------------------------------------------------


def test_state_specific_bihar_excludes_maharashtra():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    req = _make_request(
        message="Can a landlord evict a tenant for non-payment of rent?",
        language="en",
        state="Bihar",
    )
    resp = process_nyayasathi_chat(req)

    assert resp.answerStatus == AnswerStatus.supported
    urls = [s.url for s in resp.sources]
    assert any("bihar-rent-control-1982" in u for u in urls)
    assert not any("maharashtra-rent-control-1999" in u for u in urls)
    assert resp.disclaimer is not None


def test_state_specific_maharashtra_excludes_bihar():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    req = _make_request(
        message="Can a landlord evict a tenant for non-payment of rent?",
        language="en",
        state="Maharashtra",
    )
    resp = process_nyayasathi_chat(req)

    assert resp.answerStatus == AnswerStatus.supported
    urls = [s.url for s in resp.sources]
    assert any("maharashtra-rent-control-1999" in u for u in urls)
    assert not any("bihar-rent-control-1982" in u for u in urls)
    assert resp.disclaimer is not None


# ---------------------------------------------------------------------------
# TC-5: Missing state for state-specific question → needs_clarification
# ---------------------------------------------------------------------------


def test_missing_state_returns_needs_clarification():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    req = _make_request(
        message="Can a landlord evict a tenant under state rent control law?",
        language="en",
        state=None,
    )
    resp = process_nyayasathi_chat(req)

    assert resp.answerStatus == AnswerStatus.needs_clarification
    assert resp.sources == []
    assert "state" in resp.answer.lower()
    assert resp.disclaimer and "Disclaimer" in resp.disclaimer


# ---------------------------------------------------------------------------
# TC-6: Empty collection (no sources) → insufficient_information + disclaimer
# ---------------------------------------------------------------------------


def test_empty_collection_returns_insufficient_with_disclaimer():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as empty_dir:
        get_nyayasathi_collection.cache_clear()
        with patch("app.nyayasathi.service.get_settings") as mock_s:
            from app.core.config import Settings

            mock_s.return_value = Settings(
                llm_provider="mock",
                embedding_provider="local",
                embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
                chroma_persist_dir=empty_dir,
                retrieval_top_k=5,
                retrieval_threshold=0.30,
                nyayasathi_data_path="/nonexistent",
                env="development",
                ai_service_api_key="",
            )
            req = _make_request(
                message="How can I file a consumer complaint?",
                language="en",
                state="Bihar",
            )
            resp = process_nyayasathi_chat(req)
        get_nyayasathi_collection.cache_clear()

    assert resp.answerStatus == AnswerStatus.insufficient_information
    assert resp.sources == []
    assert resp.disclaimer and "Disclaimer" in resp.disclaimer


# ---------------------------------------------------------------------------
# TC-7: Out-of-scope question → insufficient_information + disclaimer
# ---------------------------------------------------------------------------


def test_out_of_scope_question_returns_insufficient(ingested_nyaya_chroma):
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    with patch("app.nyayasathi.service.get_settings") as mock_s:
        from app.core.config import Settings

        # Use standard 0.30 threshold so non-legal query falls below threshold
        mock_s.return_value = Settings(
            llm_provider="mock",
            embedding_provider="local",
            embedding_model="paraphrase-multilingual-MiniLM-L12-v2",
            chroma_persist_dir=ingested_nyaya_chroma,
            retrieval_top_k=5,
            retrieval_threshold=0.30,
            nyayasathi_data_path=str(NYAYA_FIXTURES_DIR),
            env="development",
            ai_service_api_key="",
        )
        req = _make_request(
            message="What fertilizer should I apply to my tomato plants?",
            language="en",
            state="Bihar",
        )
        resp = process_nyayasathi_chat(req)

    assert resp.answerStatus == AnswerStatus.insufficient_information
    assert resp.sources == []
    assert resp.disclaimer and "Disclaimer" in resp.disclaimer


# ---------------------------------------------------------------------------
# TC-8: Hallucination trap (made-up section number)
# ---------------------------------------------------------------------------


def test_hallucination_trap_does_not_confirm_fake_section():
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import AnswerStatus

    get_nyayasathi_collection.cache_clear()
    req = _make_request(
        message="What is the penalty under Section 999Z of the Consumer Protection Act?",
        language="en",
        state="Bihar",
    )
    resp = process_nyayasathi_chat(req)

    assert resp.answerStatus == AnswerStatus.insufficient_information
    assert "cannot verify or confirm" in resp.answer.lower()
    assert resp.disclaimer and "Disclaimer" in resp.disclaimer
