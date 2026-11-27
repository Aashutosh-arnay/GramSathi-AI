"""Stand-alone ingestion script for FarmSathi documents.

Run from inside the ai-service/ directory:

    .venv/Scripts/python.exe -m app.farmsathi.ingest [--force]

Options
-------
--force   Re-ingest even if the collection already contains data.
"""
from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest FarmSathi PDF documents into Chroma.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even when the collection already has data.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop and rebuild the collection from scratch so stale chunks are removed.",
    )
    args = parser.parse_args()

    from app.core.config import get_settings
    from app.services.embedding_service import get_embedding_service
    from app.farmsathi.knowledge_base import ingest_farmsathi_data

    settings = get_settings()
    logger.info("Loading embedding service …")
    embedding_svc = get_embedding_service()

    n = ingest_farmsathi_data(
        data_path=settings.farmsathi_data_path,
        persist_dir=settings.chroma_persist_dir,
        embedding_service=embedding_svc,
        force_reingest=args.force,
        rebuild=args.rebuild,
    )
    logger.info("Done. %d chunks in the FarmSathi collection.", n)


if __name__ == "__main__":
    main()
