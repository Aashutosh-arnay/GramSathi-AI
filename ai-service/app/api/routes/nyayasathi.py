"""POST /api/v1/nyayasathi/chat – NyayaSathi AI legal information endpoint.

Phase C: delegates to the real jurisdiction-aware legal RAG pipeline in
app.nyayasathi.service.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

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
    logger.info(
        "NyayaSathi request [%s] lang=%s state=%s msg='%s…'",
        request.requestId,
        request.language,
        request.context.state,
        request.message[:50],
    )
    return process_nyayasathi_chat(request)
