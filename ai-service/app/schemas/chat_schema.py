"""Shared Pydantic request, response and error schemas.

Defined exactly as described in Section 6 of the GramSathi AI
AI-services roadmap.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AnswerStatus(str, Enum):
    """Possible values for the answerStatus field (Section 6.2)."""

    supported = "supported"
    needs_clarification = "needs_clarification"
    insufficient_information = "insufficient_information"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class HistoryMessage(BaseModel):
    role: MessageRole
    content: str


class FarmSathiContext(BaseModel):
    state: str | None = None
    district: str | None = None
    crop: str | None = None
    cropStage: str | None = None


class NyayaSathiContext(BaseModel):
    country: str | None = "India"
    state: str | None = None
    category: str | None = None


class Source(BaseModel):
    title: str
    publisher: str
    url: str
    publishedAt: date | None = None
    retrievedAt: date | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class FarmSathiChatRequest(BaseModel):
    requestId: str = Field(..., description="Unique identifier for this request.")
    conversationId: str = Field(..., description="MongoDB conversation document ID.")
    message: str = Field(..., min_length=1, description="The user's question.")
    language: str = Field("en", description="ISO 639-1 language code (e.g. 'en', 'hi').")
    history: list[HistoryMessage] = Field(
        default_factory=list,
        description="Recent conversation turns (not the full history).",
    )
    context: FarmSathiContext = Field(default_factory=FarmSathiContext)
    attachments: list[Any] = Field(default_factory=list)


class NyayaSathiChatRequest(BaseModel):
    requestId: str = Field(..., description="Unique identifier for this request.")
    conversationId: str = Field(..., description="MongoDB conversation document ID.")
    message: str = Field(..., min_length=1, description="The user's legal question.")
    language: str = Field("en", description="ISO 639-1 language code.")
    history: list[HistoryMessage] = Field(default_factory=list)
    context: NyayaSathiContext = Field(default_factory=NyayaSathiContext)
    attachments: list[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ResponseMetadata(BaseModel):
    service: str
    version: str = "1.0"


class ChatResponse(BaseModel):
    requestId: str
    answer: str
    language: str
    answerStatus: AnswerStatus
    sources: list[Source] = Field(default_factory=list)
    followUpQuestions: list[str] = Field(default_factory=list)
    disclaimer: str | None = None
    metadata: ResponseMetadata


# ---------------------------------------------------------------------------
# Error response schema
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    requestId: str | None = None
    error: ErrorDetail
