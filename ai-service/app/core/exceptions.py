"""Custom exception types and global FastAPI exception handlers."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AIServiceError(Exception):
    """Base class for all AI-service errors."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        http_status: int = 500,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.http_status = http_status
        self.request_id = request_id


class RetrievalUnavailableError(AIServiceError):
    def __init__(self, request_id: str | None = None) -> None:
        super().__init__(
            code="RETRIEVAL_UNAVAILABLE",
            message="Unable to retrieve relevant information.",
            retryable=True,
            http_status=503,
            request_id=request_id,
        )


class LLMUnavailableError(AIServiceError):
    def __init__(self, request_id: str | None = None) -> None:
        super().__init__(
            code="LLM_UNAVAILABLE",
            message="The language model service is currently unavailable.",
            retryable=True,
            http_status=503,
            request_id=request_id,
        )


class LLMRateLimitedError(AIServiceError):
    def __init__(self, request_id: str | None = None) -> None:
        super().__init__(
            code="LLM_RATE_LIMITED",
            message="The language model rate limit or quota was exceeded. Please try again shortly.",
            retryable=True,
            http_status=429,
            request_id=request_id,
        )


class LLMConfigError(AIServiceError):
    def __init__(
        self,
        message: str = "Language model service configuration error.",
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            code="LLM_CONFIG_ERROR",
            message=message,
            retryable=False,
            http_status=500,
            request_id=request_id,
        )


def _extract_request_id_from_exc(exc: RequestValidationError) -> str | None:
    """Best-effort extraction of requestId from a failed validation body."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        rid = body.get("requestId")
        if isinstance(rid, str) and rid.strip():
            return rid
    return None


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to a FastAPI application."""

    @app.exception_handler(AIServiceError)
    async def ai_service_error_handler(
        request: Request, exc: AIServiceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "requestId": exc.request_id,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "retryable": exc.retryable,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "Invalid request payload.")
        message = f"{loc}: {msg}" if loc else msg
        return JSONResponse(
            status_code=422,
            content={
                "requestId": _extract_request_id_from_exc(exc),
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "retryable": False,
                },
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "requestId": None,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                    "retryable": False,
                },
            },
        )
