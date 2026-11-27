"""FarmSathi knowledge-base management.

Responsibilities
----------------
1. Build and persist a Chroma vector store from PDF files in
   ``FARMSATHI_DATA_PATH``.
2. Expose ``get_farmsathi_collection()`` so the retrieval service can query it.

Sidecar JSON format
-------------------
Every PDF must have a sibling ``<pdf-stem>.json`` with these fields
(all optional except ``source_title`` and ``url``):

.. code-block:: json

    {
        "source_title": "ICAR Wheat Production Guide",
        "publisher": "ICAR",
        "url": "https://icar.org.in/wheat-guide",
        "topic": "wheat production",
        "language": "en",
        "published_date": "2023-01-15",
        "retrieval_date": "2026-11-26",
        "region": "North India"
    }

PDFs without a sidecar are skipped with a WARNING.
If the data folder is empty or absent the service starts normally and
returns ``insufficient_information`` on every query.
"""
from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Chunk settings
_CHUNK_SIZE = 500          # characters
_CHUNK_OVERLAP = 80        # characters
_COLLECTION_NAME = "farmsathi_v1"


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------


def _extract_text_from_pdf(path: Path) -> str:
    """Extract plain text from a PDF using PyMuPDF."""
    import sys

    if sys.platform == "win32":
        scripts_dir = os.path.join(sys.prefix, "Scripts")
        if os.path.isdir(scripts_dir):
            os.add_dll_directory(scripts_dir)

    try:
        import pymupdf as fitz  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is not installed. Run: pip install pymupdf"
        ) from exc

    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and common PDF artefacts."""
    text = re.sub(r"\s*\n\s*\n\s*", "\n\n", text)   # collapse blank lines
    text = re.sub(r"[ \t]+", " ", text)               # collapse spaces/tabs
    text = re.sub(r"\f", "\n", text)                  # form-feeds → newline
    return text.strip()


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split *text* into overlapping character-based chunks."""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def _load_sidecar(pdf_path: Path) -> dict[str, Any] | None:
    """Load the sidecar JSON for *pdf_path*, or return None if absent."""
    sidecar = pdf_path.with_suffix(".json")
    if not sidecar.exists():
        logger.warning(
            "No sidecar JSON for '%s' — skipping this PDF. "
            "Create '%s' with source metadata.",
            pdf_path.name,
            sidecar.name,
        )
        return None
    try:
        with sidecar.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not read sidecar '%s': %s — skipping.", sidecar, exc)
        return None


# ---------------------------------------------------------------------------
# Chroma helpers
# ---------------------------------------------------------------------------


def _get_or_create_collection(persist_dir: str, embedding_fn):
    """Return (or create) the persistent Chroma collection."""
    try:
        import chromadb  # type: ignore[import]
        from chromadb.config import Settings as ChromaSettings
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is not installed. Run: pip install chromadb"
        ) from exc

    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )
    return client, collection


def _chroma_embedding_fn(embedding_service):
    """Wrap our EmbeddingService in Chroma's EmbeddingFunction interface."""
    try:
        from chromadb import EmbeddingFunction, Documents, Embeddings
    except ImportError:
        from chromadb.api.types import EmbeddingFunction, Documents, Embeddings  # type: ignore[no-redef]

    class _Fn(EmbeddingFunction):
        def __init__(self) -> None:
            pass

        @staticmethod
        def name() -> str:
            return "gramsathi-local"

        def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
            return embedding_service.embed_documents(list(input))

    return _Fn()


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def ingest_farmsathi_data(
    data_path: str,
    persist_dir: str,
    embedding_service,
    *,
    force_reingest: bool = False,
    rebuild: bool = False,
) -> int:
    """Ingest PDFs from *data_path* into Chroma.

    Files whose names start with ``_`` are ignored.
    If ``rebuild=True``, the existing collection is dropped and rebuilt.
    """
    path = Path(data_path)
    if not path.exists():
        logger.warning("FARMSATHI_DATA_PATH '%s' does not exist — no data to ingest.", data_path)
        return 0

    pdfs = [p for p in sorted(path.glob("*.pdf")) if not p.name.startswith("_")]
    if not pdfs:
        logger.info("No PDF files found in '%s' — knowledge base is empty.", data_path)
        return 0

    fn = _chroma_embedding_fn(embedding_service)
    _client, collection = _get_or_create_collection(persist_dir, fn)

    if rebuild:
        logger.info("Rebuilding FarmSathi collection '%s' …", _COLLECTION_NAME)
        try:
            _client.delete_collection(name=_COLLECTION_NAME)
        except Exception:
            pass
        get_farmsathi_collection.cache_clear()
        _client, collection = _get_or_create_collection(persist_dir, fn)
    elif not force_reingest and collection.count() > 0:
        logger.info(
            "FarmSathi Chroma collection already has %d chunks — skipping ingestion. "
            "Set force_reingest=True to re-ingest.",
            collection.count(),
        )
        return collection.count()

    today = date.today().isoformat()
    total_chunks = 0
    skipped_pdfs = 0

    for pdf in pdfs:
        meta = _load_sidecar(pdf)
        if meta is None:
            skipped_pdfs += 1
            continue

        logger.info("Ingesting '%s' …", pdf.name)
        try:
            raw = _extract_text_from_pdf(pdf)
        except Exception as exc:
            logger.error("Failed to extract text from '%s': %s — skipping.", pdf.name, exc)
            skipped_pdfs += 1
            continue

        clean = _clean_text(raw)
        chunks = _chunk_text(clean)
        if not chunks:
            logger.warning("'%s' produced no text chunks — skipping.", pdf.name)
            continue

        ids = [f"{pdf.stem}__{i}" for i in range(len(chunks))]
        chunk_meta = [
            {
                "source_title": meta.get("source_title", pdf.stem),
                "publisher": meta.get("publisher", ""),
                "url": meta.get("url", ""),
                "topic": meta.get("topic", ""),
                "language": meta.get("language", "en"),
                "published_date": meta.get("published_date", ""),
                "retrieval_date": meta.get("retrieval_date", today),
                "region": meta.get("region", ""),
                "source_file": pdf.name,
            }
            for _ in chunks
        ]

        # Upsert in batches of 100 to stay within Chroma limits
        batch_size = 100
        for start in range(0, len(chunks), batch_size):
            collection.upsert(
                ids=ids[start : start + batch_size],
                documents=chunks[start : start + batch_size],
                metadatas=chunk_meta[start : start + batch_size],
            )

        total_chunks += len(chunks)
        logger.info("  → %d chunks stored for '%s'.", len(chunks), pdf.name)

    if skipped_pdfs:
        logger.warning("%d PDF(s) skipped (missing sidecar or extraction error).", skipped_pdfs)
    logger.info("Ingestion complete: %d total chunks in collection.", total_chunks)
    return total_chunks


# ---------------------------------------------------------------------------
# Public accessor (used by the retrieval service)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_farmsathi_collection(persist_dir: str, embedding_service_id: int):
    """Return the Chroma collection (cached singleton).

    ``embedding_service_id`` is used only to make the cache key unique per
    embedding service instance; pass ``id(embedding_service)``.
    """
    from app.services.embedding_service import get_embedding_service

    svc = get_embedding_service()
    fn = _chroma_embedding_fn(svc)

    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("chromadb not installed. Run: pip install chromadb") from exc

    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=fn,
    )
    return collection
