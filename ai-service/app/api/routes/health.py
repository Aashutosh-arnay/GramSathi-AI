"""GET /health – AI service liveness probe."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="AI service health check",
    description="Returns 200 OK when the AI service is running.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="gramsathi-ai-service",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        version="1.0.0",
    )
