"""Shared PDF extraction, text cleaning, chunking, sidecar, and Chroma helpers.

Used by both FarmSathi and NyayaSathi knowledge bases to avoid duplicating
document-processing logic.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 80


def extract_text_from_pdf(path: Path) -> str:
    """Extract plain text from a PDF using PyMuPDF."""
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
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def clean_text(text: str) -> str:
    """Remove excessive whitespace and common PDF artefacts."""
    text = re.sub(r"\s*\n\s*\n\s*", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\f", "\n", text)
    return text.strip()


def chunk_text(
    text: str,
    size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
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


def load_sidecar(pdf_path: Path) -> dict[str, Any] | None:
    """Load the sibling ``.json`` sidecar for *pdf_path*, or return None."""
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


def chroma_embedding_fn(embedding_service):
    """Wrap an EmbeddingService in Chroma's EmbeddingFunction interface."""
    try:
        from chromadb import Documents, EmbeddingFunction, Embeddings
    except ImportError:
        from chromadb.api.types import Documents, EmbeddingFunction, Embeddings  # type: ignore[no-redef]

    class _Fn(EmbeddingFunction):
        def __init__(self) -> None:
            pass

        @staticmethod
        def name() -> str:
            return "gramsathi-local"

        def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
            return embedding_service.embed_documents(list(input))

    return _Fn()


def get_or_create_collection(persist_dir: str, collection_name: str, embedding_fn):
    """Return ``(client, collection)`` for a persistent Chroma collection."""
    try:
        import chromadb  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is not installed. Run: pip install chromadb"
        ) from exc

    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )
    return client, collection
