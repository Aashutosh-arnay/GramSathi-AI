"""NyayaSathi AI service – query analysis, jurisdiction-aware retrieval,
hallucination checks, and response assembly.
"""
from __future__ import annotations

import logging
import re
from datetime import date

from app.core.config import get_settings
from app.core.exceptions import AIServiceError, LLMUnavailableError, RetrievalUnavailableError
from app.farmsathi.prompts import summarise_history
from app.nyayasathi.knowledge_base import get_nyayasathi_collection
from app.nyayasathi.prompts import (
    NYAYASATHI_SYSTEM_PROMPT,
    build_nyayasathi_user_message,
    get_legal_disclaimer,
)
from app.schemas.chat_schema import (
    AnswerStatus,
    ChatResponse,
    NyayaSathiChatRequest,
    ResponseMetadata,
    Source,
)
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import RetrievedChunk, RetrievalService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Query analysis: legal categories
# ---------------------------------------------------------------------------

LEGAL_CATEGORIES = (
    "consumer",
    "labour",
    "property",
    "family",
    "criminal",
    "civil",
    "constitutional",
    "legal_aid",
    "other",
)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "consumer": ("consumer", "refund", "defective", "warranty", "उपभोक्ता", "शिकायत"),
    "labour": ("labour", "labor", "wage", "salary", "worker", "epf", "मजदूर", "श्रमिक", "वेतन"),
    "property": ("property", "land", "rent", "tenant", "landlord", "eviction", "mutation", "ज़मीन", "संपत्ति", "किराया"),
    "family": ("family", "marriage", "divorce", "maintenance", "alimony", "custody", "विवाह", "तलाक", "भरण"),
    "criminal": ("criminal", "fir", "police", "arrest", "bail", "theft", "fraud", "अपराध", "एफआईआर", "पुलिस", "जमानत"),
    "civil": ("civil", "money", "debt", "loan", "contract", "notice", "recovery", "पैसे", "कर्ज", "अनुबंध", "नोटिस"),
    "constitutional": ("constitution", "fundamental right", "article", "writ", "संविधान", "मौलिक अधिकार"),
    "legal_aid": ("legal aid", "free legal", "nalsa", "slsa", "lok adalat", "मुफ्त कानूनी", "विधिक सेवा", "लोक अदालत"),
}

_STATE_SPECIFIC_HINTS = (
    "state law",
    "state act",
    "state government",
    "rent control",
    "eviction",
    "tenant",
    "landlord",
    "land revenue",
    "mutation",
    "tehsil",
    "stamp duty",
    "राज्य",
    "किराया",
    "दाखिल",
    "भू-राजस्व",
)

_SECTION_PATTERN = re.compile(r"\b(?:section|sec\.?|धारा)\s+([0-9]+[a-zA-Z\-]*)\b", re.IGNORECASE)


def classify_legal_category(message: str, context_category: str | None = None) -> str:
    """Classify the legal question into one of ``LEGAL_CATEGORIES``."""
    if context_category:
        norm = context_category.strip().lower().replace(" ", "_")
        for cat in LEGAL_CATEGORIES:
            if cat == norm or cat in norm:
                return cat

    msg_lower = message.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return cat
    return "other"


def _is_state_specific_query(message: str) -> bool:
    msg_lower = message.lower()
    return any(hint in msg_lower for hint in _STATE_SPECIFIC_HINTS)


def _extract_asked_sections(message: str) -> list[str]:
    return [m.strip().lower() for m in _SECTION_PATTERN.findall(message)]


def _section_in_chunks(section_token: str, chunks: list[RetrievedChunk]) -> bool:
    for c in chunks:
        sec_meta = str((c.metadata or {}).get("section_number", "")).lower()
        if section_token in sec_meta or section_token in c.text.lower():
            return True
    return False


def _chunks_to_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    """Build deduplicated Source objects solely from retrieved chunk metadata."""
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

        meta = chunk.metadata or {}
        title = chunk.source_title or meta.get("document_title") or "(unknown)"
        sec = meta.get("section_number")
        if sec and sec not in title:
            title = f"{title} ({sec})"

        sources.append(
            Source(
                title=title,
                publisher=chunk.publisher or meta.get("issuing_authority") or "(unknown)",
                url=chunk.url,
                publishedAt=pub_date,
                retrievedAt=ret_date,
            )
        )
    return sources


def _build_jurisdiction_filter(state: str | None) -> dict:
    """Build Chroma ``where`` filter for central + optional matching state."""
    if state and state.strip():
        state_lower = state.strip().lower()
        return {
            "$or": [
                {"jurisdiction": "central"},
                {
                    "$and": [
                        {"jurisdiction": "state"},
                        {"applicable_state_lower": state_lower},
                    ]
                },
            ]
        }
    return {"jurisdiction": "central"}


def _state_clarification_response(request_id: str, language: str) -> ChatResponse:
    is_hi = (language or "en").lower().startswith("hi")
    answer = (
        "सटीक कानूनी जानकारी देने के लिए कृपया बताएं कि आप भारत के किस राज्य में स्थित हैं?"
        if is_hi
        else "To give you accurate legal information, could you please share which state in India you are located in?"
    )
    follow_ups = (
        ["आप किस राज्य में स्थित हैं?", "यह मामला किस प्रकार का है?"]
        if is_hi
        else ["Which state in India does this matter concern?", "Could you share any relevant details?"]
    )
    return ChatResponse(
        requestId=request_id,
        answer=answer,
        language=language,
        answerStatus=AnswerStatus.needs_clarification,
        sources=[],
        followUpQuestions=follow_ups,
        disclaimer=get_legal_disclaimer(language),
        metadata=ResponseMetadata(service="nyayasathi"),
    )


def _insufficient_response(
    request_id: str,
    language: str,
    *,
    custom_answer: str | None = None,
) -> ChatResponse:
    is_hi = (language or "en").lower().startswith("hi")
    default_answer = (
        "माफ़ कीजिए, उपलब्ध सत्यापित कानूनी स्रोतों में इस प्रश्न का उत्तर देने के लिए पर्याप्त जानकारी नहीं है। "
        "कृपया किसी योग्य वकील या अपने नज़दीकी विधिक सेवा प्राधिकरण (NALSA / SLSA) से संपर्क करें।"
        if is_hi
        else "I'm sorry, there is insufficient verified legal information in my knowledge base to answer this question. "
        "Please consult a qualified advocate or contact your nearest Legal Services Authority (NALSA / SLSA)."
    )
    follow_ups = (
        ["आप किस राज्य में स्थित हैं?", "यह मामला किस कानून या विभाग से जुड़ा है?"]
        if is_hi
        else ["Which state are you located in?", "What type of legal matter does this concern?"]
    )
    return ChatResponse(
        requestId=request_id,
        answer=custom_answer or default_answer,
        language=language,
        answerStatus=AnswerStatus.insufficient_information,
        sources=[],
        followUpQuestions=follow_ups,
        disclaimer=get_legal_disclaimer(language),
        metadata=ResponseMetadata(service="nyayasathi"),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def process_nyayasathi_chat(request: NyayaSathiChatRequest) -> ChatResponse:
    """Full NyayaSathi pipeline: classify → jurisdiction-filtered retrieve → guard → LLM."""
    settings = get_settings()
    language = request.language or "en"
    state = request.context.state
    category = classify_legal_category(request.message, request.context.category)
    logger.info(
        "NyayaSathi [%s] category=%s state=%s lang=%s",
        request.requestId,
        category,
        state,
        language,
    )

    # ── 1. Initialise retrieval ─────────────────────────────────────────────
    try:
        embedding_svc = get_embedding_service()
        collection = get_nyayasathi_collection(
            persist_dir=settings.chroma_persist_dir,
            embedding_service_id=id(embedding_svc),
        )
        retrieval = RetrievalService(
            collection=collection,
            threshold=settings.retrieval_threshold,
            top_k=settings.retrieval_top_k,
        )
    except Exception as exc:
        logger.error("Failed to initialise NyayaSathi retrieval: %s", exc)
        raise RetrievalUnavailableError(request_id=request.requestId) from exc

    # ── 2. Missing state check for state-specific queries ───────────────────
    if not state and _is_state_specific_query(request.message):
        logger.info("[%s] State-specific query without state → needs_clarification.", request.requestId)
        return _state_clarification_response(request.requestId, language)

    # ── 3. Jurisdiction-filtered semantic search ────────────────────────────
    try:
        where_filter = _build_jurisdiction_filter(state)
        chunks = retrieval.search(request.message, where=where_filter)

        # If no central chunks matched and state was omitted, check if a state
        # document would have matched — if so, ask the user for their state
        # rather than leaking another state's law.
        if not chunks and not state:
            state_probe = retrieval.search(
                request.message, where={"jurisdiction": "state"}
            )
            if state_probe:
                logger.info(
                    "[%s] State-level docs exist but state is missing → needs_clarification.",
                    request.requestId,
                )
                return _state_clarification_response(request.requestId, language)
    except Exception as exc:
        logger.error("NyayaSathi retrieval search failed: %s", exc)
        raise RetrievalUnavailableError(request_id=request.requestId) from exc

    # ── 4. Below threshold → insufficient_information (do NOT call LLM) ─────
    if not chunks:
        return _insufficient_response(request.requestId, language)

    # ── 5. Hallucination trap: verify any asked section numbers exist ───────
    asked_sections = _extract_asked_sections(request.message)
    missing_sections = [
        sec for sec in asked_sections if not _section_in_chunks(sec, chunks)
    ]
    if missing_sections:
        is_hi = language.lower().startswith("hi")
        sec_str = ", ".join(missing_sections)
        msg = (
            f"उपलब्ध आधिकारिक कानूनी दस्तावेज़ों में धारा {sec_str} की पुष्टि नहीं हो सकी। "
            "कृपया किसी योग्य वकील या विधिक सेवा प्राधिकरण (NALSA / SLSA) से सत्यापन कराएं।"
            if is_hi
            else f"I cannot verify or confirm Section {sec_str} from the available official legal sources. "
            "Please verify this provision with a qualified advocate or your nearest Legal Services Authority (NALSA / SLSA)."
        )
        return _insufficient_response(request.requestId, language, custom_answer=msg)

    # ── 6. Call LLM ─────────────────────────────────────────────────────────
    history_summary = summarise_history(
        [{"role": m.role.value, "content": m.content} for m in request.history]
    )
    user_msg = build_nyayasathi_user_message(
        question=request.message,
        language=language,
        chunks=chunks,
        country=request.context.country,
        state=state,
        category=category,
        history_summary=history_summary,
    )

    try:
        llm = get_llm_service()
        answer = llm.generate(NYAYASATHI_SYSTEM_PROMPT, user_msg, language=language)
    except AIServiceError as exc:
        exc.request_id = request.requestId
        raise
    except Exception as exc:
        logger.error("NyayaSathi LLM generation failed: %s", exc)
        raise LLMUnavailableError(request_id=request.requestId) from exc

    # ── 7. Append effective date note if present in metadata and omitted ────
    effective_dates = sorted(
        {
            str((c.metadata or {}).get("effective_date", "")).strip()
            for c in chunks
            if (c.metadata or {}).get("effective_date")
        }
    )
    if effective_dates and not any(d in answer for d in effective_dates):
        is_hi = language.lower().startswith("hi")
        dates_str = ", ".join(effective_dates)
        note = (
            f"\n\nप्रभावी तिथि (Effective Date): {dates_str}"
            if is_hi
            else f"\n\nEffective Date of cited provision(s): {dates_str}"
        )
        answer = f"{answer}{note}"

    # ── 8. Assemble response with verified sources + mandatory disclaimer ───
    sources = _chunks_to_sources(chunks)

    return ChatResponse(
        requestId=request.requestId,
        answer=answer,
        language=language,
        answerStatus=AnswerStatus.supported,
        sources=sources,
        followUpQuestions=[],
        disclaimer=get_legal_disclaimer(language),
        metadata=ResponseMetadata(service="nyayasathi"),
    )
