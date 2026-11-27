"""POST /api/v1/farmsathi/chat – FarmSathi AI agricultural chat endpoint."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends

from app.core.exceptions import AIServiceError
from app.core.security import require_api_key
from app.farmsathi.service import process_farmsathi_chat
from app.schemas.chat_schema import ChatResponse, FarmSathiChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/farmsathi",
    tags=["FarmSathi AI"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="FarmSathi agricultural question answering",
    description=(
        "Send an agricultural question in Hindi or English. "
        "Returns an AI-generated answer grounded in the FarmSathi knowledge base, "
        "with source citations from verified agricultural documents."
    ),
)
async def farmsathi_chat(request: FarmSathiChatRequest) -> ChatResponse:
    """Full RAG pipeline: embed → retrieve → (optionally) generate → respond."""
    t0 = time.perf_counter()
    try:
        resp = process_farmsathi_chat(request)
    except AIServiceError as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "requestId=%s endpoint=/api/v1/farmsathi/chat errorCode=%s latency_ms=%d",
            request.requestId,
            exc.code,
            latency_ms,
        )
        raise

    latency_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "requestId=%s endpoint=/api/v1/farmsathi/chat answerStatus=%s latency_ms=%d",
        request.requestId,
        resp.answerStatus.value,
        latency_ms,
    )
    return resp
