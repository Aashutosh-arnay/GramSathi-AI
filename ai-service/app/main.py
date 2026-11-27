"""FastAPI application entry point for the GramSathi AI service."""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import farmsathi, health, meta, nyayasathi
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

logger = logging.getLogger(__name__)


def _check_production_safety(settings) -> None:
    """Refuse to start in production when critical settings are missing."""
    if settings.env.lower() == "production":
        if not settings.ai_service_api_key:
            logger.critical(
                "FATAL: ENV=production but AI_SERVICE_API_KEY is not set. "
                "Set a strong secret before deploying."
            )
            sys.exit(1)


settings = get_settings()
_check_production_safety(settings)

app = FastAPI(
    title="GramSathi AI Service",
    description=(
        "Internal AI service powering FarmSathi (agricultural assistant) and "
        "NyayaSathi (legal information assistant) for the GramSathi AI platform."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS – restrict to the Node.js backend in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to backend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(meta.router)
app.include_router(farmsathi.router)
app.include_router(nyayasathi.router)


# ---------------------------------------------------------------------------
# Startup: auto-ingest FarmSathi data if the collection is empty
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def _startup_ingest() -> None:
    """On startup, trigger FarmSathi and NyayaSathi ingestion if empty."""
    try:
        from app.farmsathi.knowledge_base import ingest_farmsathi_data
        from app.nyayasathi.knowledge_base import ingest_nyayasathi_data
        from app.services.embedding_service import get_embedding_service

        embedding_svc = get_embedding_service()

        n_farm = ingest_farmsathi_data(
            data_path=settings.farmsathi_data_path,
            persist_dir=settings.chroma_persist_dir,
            embedding_service=embedding_svc,
            force_reingest=False,
        )
        logger.info("FarmSathi knowledge base ready (%d chunks).", n_farm)

        n_nyaya = ingest_nyayasathi_data(
            data_path=settings.nyayasathi_data_path,
            persist_dir=settings.chroma_persist_dir,
            embedding_service=embedding_svc,
            force_reingest=False,
        )
        logger.info("NyayaSathi knowledge base ready (%d chunks).", n_nyaya)
    except Exception as exc:
        # Non-fatal: the service starts even without data (returns insufficient_information)
        logger.warning("Startup ingestion skipped: %s", exc)
