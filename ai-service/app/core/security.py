"""Internal API-key authentication for the AI service.

The Node.js backend passes the shared secret in the
``AI-Service-Api-Key`` HTTP header.  This is entirely separate from the
user-facing JWT that the backend manages.
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_api_key(
    ai_service_api_key: str | None = Header(
        default=None,
        alias="AI-Service-Api-Key",
        description="Shared internal API key (AI_SERVICE_API_KEY env var).",
    ),
) -> None:
    """FastAPI dependency that validates the internal service API key.

    If ``AI_SERVICE_API_KEY`` is not set in the environment (empty string),
    authentication is skipped so the service can run without auth in local
    development.  Set a strong secret in production.
    """
    settings = get_settings()
    expected = settings.ai_service_api_key

    if not expected:
        # Dev mode: no key configured – skip auth entirely.
        return

    if ai_service_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "requestId": None,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing AI-Service-Api-Key header.",
                    "retryable": False,
                },
            },
        )
