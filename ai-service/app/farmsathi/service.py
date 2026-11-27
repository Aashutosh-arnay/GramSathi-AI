"""FarmSathi AI service – orchestrates retrieval → LLM → response assembly.

Pipeline
--------
1. Embed the user's question.
2. Search the Chroma collection (top-k, threshold-filtered).
3. If no chunks pass the threshold → return ``insufficient_information``.
4. If the question lacks critical agricultural context (crop or state when no
   chunks cover it) → return ``needs_clarification``.
5. Build the LLM prompt from retrieved chunks and call the LLM.
6. Assemble ``ChatResponse`` with sources taken exclusively from chunk metadata.
"""
from __future__ import annotations

import logging
from datetime import date

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, LLMUnavailableError, RetrievalUnavailableError
from app.farmsathi.knowledge_base import get_farmsathi_collection
from app.farmsathi.prompts import (
    FARMSATHI_SYSTEM_PROMPT,
    build_user_message,
    summarise_history,
)
from app.schemas.chat_schema import (
    AnswerStatus,
    ChatResponse,
    FarmSathiChatRequest,
    ResponseMetadata,
    Source,
)
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import RetrievedChunk, RetrievalService

logger = logging.getLogger(__name__)

# Follow-up questions to request missing context
_FOLLOW_UPS_EN = [
    "Which crop are you growing?",
    "Which state and district are you farming in?",
    "What stage is the crop at (seedling, vegetative, flowering, harvest)?",
]
_FOLLOW_UPS_HI = [
    "आप कौन सी फसल उगा रहे हैं?",
    "आप किस राज्य और जिले में खेती करते हैं?",
    "फसल किस अवस्था में है (अंकुरण, वानस्पतिक, फूल, कटाई)?",
]


def _chunks_to_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    """Convert retrieved chunks to deduplicated Source objects.

    Only URLs that appear in the retrieved chunk metadata are returned.
    """
    seen_urls: set[str] = set()
    sources: list[Source] = []
    for chunk in chunks:
        if not chunk.url or chunk.url in seen_urls:
            continue
        seen_urls.add(chunk.url)
        try:
            pub_date = date.fromisoformat(chunk.published_date) if chunk.published_date else None
        except ValueError:
            pub_date = None
        try:
            ret_date = date.fromisoformat(chunk.retrieval_date) if chunk.retrieval_date else None
        except ValueError:
            ret_date = date.today()
        sources.append(
            Source(
                title=chunk.source_title or "(unknown)",
                publisher=chunk.publisher or "(unknown)",
                url=chunk.url,
                publishedAt=pub_date,
                retrievedAt=ret_date,
            )
        )
    return sources


def _needs_more_context(
    request: FarmSathiChatRequest,
    chunks: list[RetrievedChunk],
) -> bool:
    """Return True when the query is too vague without farmer context.

    Heuristic: if no crop and no state were given AND the retrieved chunks
    are either empty or all score < 0.5, we ask for clarification.
    """
    ctx = request.context
    has_context = bool(ctx.crop or ctx.state)
    if has_context:
        return False
    # Even without explicit context, high-scoring chunks mean the question is
    # specific enough for a general answer.
    if chunks and chunks[0].score >= 0.50:
        return False
    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def process_farmsathi_chat(request: FarmSathiChatRequest) -> ChatResponse:
    """Full FarmSathi pipeline.  Called by the FastAPI route handler."""
    settings = get_settings()
    language = request.language or "en"

    # ── 1. Get retrieval service ────────────────────────────────────────────
    try:
        embedding_svc = get_embedding_service()
        collection = get_farmsathi_collection(
            persist_dir=settings.chroma_persist_dir,
            embedding_service_id=id(embedding_svc),
        )
        retrieval = RetrievalService(
            collection=collection,
            threshold=settings.retrieval_threshold,
            top_k=settings.retrieval_top_k,
        )
    except Exception as exc:
        logger.error("Failed to initialise retrieval: %s", exc)
        raise RetrievalUnavailableError(request_id=request.requestId) from exc

    # ── 2. Semantic search ──────────────────────────────────────────────────
    try:
        chunks = retrieval.search(request.message)
    except Exception as exc:
        logger.error("Retrieval search failed: %s", exc)
        raise RetrievalUnavailableError(request_id=request.requestId) from exc

    # ── 3. No results above threshold → insufficient_information ────────────
    if not chunks:
        logger.info(
            "[%s] No chunks above threshold for question: %s",
            request.requestId,
            request.message[:60],
        )
        answer = (
            "माफ़ कीजिए, मेरे पास इस प्रश्न का उत्तर देने के लिए पर्याप्त जानकारी नहीं है।"
            if language == "hi"
            else "I'm sorry, I don't have enough information in my knowledge base to answer this question."
        )
        return ChatResponse(
            requestId=request.requestId,
            answer=answer,
            language=language,
            answerStatus=AnswerStatus.insufficient_information,
            sources=[],
            followUpQuestions=_FOLLOW_UPS_HI if language == "hi" else _FOLLOW_UPS_EN,
            disclaimer=None,
            metadata=ResponseMetadata(service="farmsathi"),
        )

    # ── 4. Needs clarification? ─────────────────────────────────────────────
    if _needs_more_context(request, chunks):
        logger.info("[%s] Returning needs_clarification.", request.requestId)
        answer = (
            "आपकी फसल और स्थान के बारे में अधिक जानकारी दें तो मैं बेहतर उत्तर दे सकता हूँ।"
            if language == "hi"
            else "Please share more details about your crop and location so I can give you a better answer."
        )
        return ChatResponse(
            requestId=request.requestId,
            answer=answer,
            language=language,
            answerStatus=AnswerStatus.needs_clarification,
            sources=[],
            followUpQuestions=_FOLLOW_UPS_HI if language == "hi" else _FOLLOW_UPS_EN,
            disclaimer=None,
            metadata=ResponseMetadata(service="farmsathi"),
        )

    # ── 5. Call LLM ─────────────────────────────────────────────────────────
    history_summary = summarise_history(
        [{"role": m.role.value, "content": m.content} for m in request.history]
    )
    user_msg = build_user_message(
        question=request.message,
        language=language,
        chunks=chunks,
        state=request.context.state,
        district=request.context.district,
        crop=request.context.crop,
        crop_stage=request.context.cropStage,
        history_summary=history_summary,
    )

    try:
        llm = get_llm_service()
        answer = llm.generate(FARMSATHI_SYSTEM_PROMPT, user_msg, language=language)
    except AIServiceError as exc:
        exc.request_id = request.requestId
        raise
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        raise LLMUnavailableError(request_id=request.requestId) from exc

    # ── 6. Assemble response – sources from chunks only ─────────────────────
    sources = _chunks_to_sources(chunks)

    return ChatResponse(
        requestId=request.requestId,
        answer=answer,
        language=language,
        answerStatus=AnswerStatus.supported,
        sources=sources,
        followUpQuestions=[],
        disclaimer=None,
        metadata=ResponseMetadata(service="farmsathi"),
    )
