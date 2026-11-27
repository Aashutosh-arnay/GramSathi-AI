"""POST /api/v1/nyayasathi/chat – NyayaSathi AI legal information endpoint."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends

from app.core.exceptions import AIServiceError
from app.core.security import require_api_key
from app.nyayasathi.service import process_nyayasathi_chat
from app.schemas.chat_schema import ChatResponse, NyayaSathiChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/nyayasathi",
    tags=["NyayaSathi AI"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="NyayaSathi legal information question answering",
    description=(
        "Send a legal question in Hindi or English. "
        "Returns general legal information with verified source citations and "
        "a mandatory legal disclaimer."
    ),
)
async def nyayasathi_chat(request: NyayaSathiChatRequest) -> ChatResponse:
    """Full legal RAG pipeline: classify → jurisdiction-filter → retrieve → generate."""
    t0 = time.perf_counter()
    try:
        resp = process_nyayasathi_chat(request)
    except AIServiceError as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "requestId=%s endpoint=/api/v1/nyayasathi/chat errorCode=%s latency_ms=%d",
            request.requestId,
            exc.code,
            latency_ms,
        )
        raise

    latency_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "requestId=%s endpoint=/api/v1/nyayasathi/chat answerStatus=%s latency_ms=%d",
        request.requestId,
        resp.answerStatus.value,
        latency_ms,
    )
    return resp
