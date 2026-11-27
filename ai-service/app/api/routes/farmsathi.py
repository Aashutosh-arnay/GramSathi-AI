"""POST /api/v1/farmsathi/chat – FarmSathi AI agricultural chat endpoint.

Phase B: delegates to the real RAG pipeline in app.farmsathi.service.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

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
    logger.info(
        "FarmSathi request [%s] lang=%s msg='%s…'",
        request.requestId,
        request.language,
        request.message[:50],
    )
    return process_farmsathi_chat(request)
