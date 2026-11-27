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
import re
from datetime import date

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, LLMUnavailableError, RetrievalUnavailableError
from app.core.states import normalize_state
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


_KNOWN_CROPS_AND_TOPICS = (
    "wheat", "rice", "paddy", "maize", "gehu", "gehun", "dhan",
    "गेहूँ", "गेहूं", "धान", "चावल", "मक्का",
    "pm-kisan", "pmkisan", "पीएम-किसान", "पीएम किसान",
    "soil health", "nmsa", "मृदा स्वास्थ्य",
    "direct seeded", "सीधी बुआई",
)

_LIVE_DATA_PATTERNS = (
    r"\bmandi\s+(?:price|rate)s?\b",
    r"\b(?:current|today'?s?|live|latest)\s+(?:mandi\s+)?(?:price|rate)s?\b",
    r"\b(?:wheat|rice|paddy|maize|tractor|crop)\s+(?:rate|price)s?\s+(?:in|at|of)\b",
    r"\btractor\s+price\b",
    r"\bweather\s+forecast\b",
    r"\brainfall\s+prediction\s+(?:for|in)\b",
    r"(?:गेहूँ|गेहूं|धान|चावल|फसल|टमाटर|मंडी)\s+(?:का\s+)?(?:ताज़ा\s*|ताजा\s*)?भाव\b",
    r"(?:आज|कल)\s+.*?(?:भाव|मंडी|मौसम)",
    r"मौसम\s+का\s+हाल",
    r"\bpmfby\b", r"\bfasal\s+bima\b", r"फसल\s+बीमा",
)

_QUOTED_PHRASE_RE = re.compile(r"['\"]([A-Za-z0-9\s\-]{4,})['\"]")
_CODE_PRODUCT_RE = re.compile(r"\b([A-Za-z]+-\d+[A-Za-z0-9]*)\b")
_CAPITALIZED_SCHEME_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9\-]+(?:\s+[A-Z][A-Za-z0-9\-]+){2,}(?:\s+\d{4})?)\b"
)


def _is_live_or_uncovered(message: str) -> bool:
    """Return True for live weather/mandi/price queries or uncovered schemes."""
    msg_lower = message.lower()
    return any(re.search(pat, msg_lower) for pat in _LIVE_DATA_PATTERNS)


def _has_unverified_named_entity(message: str, chunks: list[RetrievedChunk]) -> bool:
    """Return True if the user names a specific scheme/chemical not found in chunks."""
    combined = " ".join(c.text.lower() for c in chunks) + " " + " ".join(
        (c.source_title or "").lower() for c in chunks
    )

    # 1. Alphanumeric product/chemical code (e.g. SuperKill-999)
    for code in _CODE_PRODUCT_RE.findall(message):
        if code.lower() not in ("pm-kisan", "nmsa-shm") and code.lower() not in combined:
            return True

    # 2. Quoted ASCII phrase containing a year or product/scheme keyword
    for phrase in _QUOTED_PHRASE_RE.findall(message):
        if any(k in phrase.lower() for k in ("scheme", "subsidy", "yojana", "2025", "2026")):
            tokens = [t for t in phrase.lower().split() if len(t) > 3]
            if tokens and sum(1 for t in tokens if t in combined) < len(tokens) / 2:
                return True

    # 3. Quoted non-ASCII scheme/yojana phrase (only when explicitly naming a scheme/yojana)
    for phrase in re.findall(r"['\"]([^'\"]{4,})['\"]", message):
        if any(k in phrase for k in ("योजना", "अभियान", "स्कीम")):
            tokens = [t for t in phrase.lower().split() if len(t) > 2 and t not in ("योजना", "मुफ्त", "और", "की", "के")]
            if tokens and not any(t in combined for t in tokens):
                return True

    # 4. Multi-word capitalized scheme name with subsidy/yojana/year
    _GENERIC_WORDS = {"scheme", "yojana", "card", "mission", "india", "free", "pm-kisan", "2017", "2018", "2019", "2020"}
    for scheme in _CAPITALIZED_SCHEME_RE.findall(message):
        if any(w in scheme.lower() for w in ("scheme", "subsidy", "yojana", "2025", "2026")):
            key_words = [
                w.lower()
                for w in scheme.split()
                if len(w) > 3 and w.lower() not in _GENERIC_WORDS
            ]
            if key_words and sum(1 for w in key_words if w in combined) < max(1, len(key_words) - 1):
                return True

    return False


def _needs_more_context(
    request: FarmSathiChatRequest,
    chunks: list[RetrievedChunk],
    normalized_state: str | None = None,
) -> bool:
    """Return True when the query is too vague without crop or location context."""
    ctx = request.context
    if ctx.crop or normalized_state:
        return False

    msg_lower = request.message.lower()
    if any(tok in msg_lower for tok in _KNOWN_CROPS_AND_TOPICS):
        return False

    # Check recent history for crop/topic mention
    hist_text = " ".join(m.content.lower() for m in request.history)
    if any(tok in hist_text for tok in _KNOWN_CROPS_AND_TOPICS):
        return False

    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def process_farmsathi_chat(request: FarmSathiChatRequest) -> ChatResponse:
    """Full FarmSathi pipeline.  Called by the FastAPI route handler."""
    settings = get_settings()
    language = request.language or "en"
    normalized_state = normalize_state(request.context.state)

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

    # ── 2. Live data / uncovered scheme guard ───────────────────────────────
    if _is_live_or_uncovered(request.message):
        logger.info("[%s] Live-data or uncovered scheme query → insufficient_information.", request.requestId)
        answer = (
            "माफ़ कीजिए, मेरे पास इस विषय (जैसे ताज़ा मंडी भाव, मौसम पूर्वानुमान, या यह योजना) पर सत्यापित जानकारी उपलब्ध नहीं है।"
            if language == "hi"
            else "I'm sorry, I don't have verified information or live data for this request in my knowledge base."
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

    # ── 3. Semantic search ──────────────────────────────────────────────────
    try:
        chunks = retrieval.search(request.message)
    except Exception as exc:
        logger.error("Retrieval search failed: %s", exc)
        raise RetrievalUnavailableError(request_id=request.requestId) from exc

    # ── 4. No results above threshold → insufficient_information ────────────
    if not chunks:
        logger.info("[%s] No chunks above threshold.", request.requestId)
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

    # ── 5. Hallucination / unverified named-entity guard ────────────────────
    if _has_unverified_named_entity(request.message, chunks):
        logger.info("[%s] Unverified scheme/chemical entity → insufficient_information.", request.requestId)
        answer = (
            "माफ़ कीजिए, उपलब्ध आधिकारिक कृषि दस्तावेज़ों में इस योजना या रसायन की पुष्टि नहीं हो सकी। कृपया अपने नज़दीकी KVK या कृषि विशेषज्ञ से संपर्क करें।"
            if language == "hi"
            else "I cannot verify or confirm that specific scheme, chemical, or dosage in the available official agricultural documents. Please consult your nearest Krishi Vigyan Kendra (KVK) or an agricultural expert."
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

    # ── 6. Needs clarification? ─────────────────────────────────────────────
    if _needs_more_context(request, chunks, normalized_state=normalized_state):
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
        state=normalized_state,
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
