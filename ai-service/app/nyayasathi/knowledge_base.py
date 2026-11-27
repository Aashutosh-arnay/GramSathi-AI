"""NyayaSathi legal knowledge-base management.

Responsibilities
----------------
1. Build and persist a separate Chroma collection (``nyayasathi_v1``) from
   legal PDF files in ``NYAYASATHI_DATA_PATH``.
2. Expose ``get_nyayasathi_collection()`` for jurisdiction-aware retrieval.

Sidecar JSON format (§5.3)
--------------------------
Every PDF must have a sibling ``<pdf-stem>.json`` with these fields:

.. code-block:: json

    {
        "document_title": "Consumer Protection Act, 2019",
        "issuing_authority": "Ministry of Law and Justice, Government of India",
        "url": "https://www.indiacode.nic.in/...",
        "jurisdiction": "central",
        "applicable_state": "",
        "act_name": "Consumer Protection Act, 2019",
        "section_number": "Section 35",
        "publication_date": "2019-08-09",
        "effective_date": "2020-07-20",
        "last_updated_date": "2020-07-20",
        "retrieval_date": "2026-11-28",
        "language": "en"
    }

PDFs without a sidecar are skipped with a WARNING.
If the data folder is empty or absent the service starts normally and
returns ``insufficient_information`` on every query.
"""
from __future__ import annotations

import logging
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.services.ingestion_utils import (
    chroma_embedding_fn,
    chunk_text,
    clean_text,
    extract_text_from_pdf,
    get_or_create_collection,
    load_sidecar,
)

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "nyayasathi_v1"


def ingest_nyayasathi_data(
    data_path: str,
    persist_dir: str,
    embedding_service,
    *,
    force_reingest: bool = False,
    rebuild: bool = False,
) -> int:
    """Ingest legal PDFs from *data_path* into the NyayaSathi Chroma collection.

    Files whose names start with ``_`` are ignored.
    If ``rebuild=True``, the existing collection is dropped and rebuilt.
    """
    path = Path(data_path)
    if not path.exists():
        logger.warning(
            "NYAYASATHI_DATA_PATH '%s' does not exist — no legal data to ingest.",
            data_path,
        )
        return 0

    pdfs = [p for p in sorted(path.glob("*.pdf")) if not p.name.startswith("_")]
    if not pdfs:
        logger.info("No PDF files found in '%s' — legal knowledge base is empty.", data_path)
        return 0

    fn = chroma_embedding_fn(embedding_service)
    _client, collection = get_or_create_collection(persist_dir, _COLLECTION_NAME, fn)

    if rebuild:
        logger.info("Rebuilding NyayaSathi collection '%s' …", _COLLECTION_NAME)
        try:
            _client.delete_collection(name=_COLLECTION_NAME)
        except Exception:
            pass
        get_nyayasathi_collection.cache_clear()
        _client, collection = get_or_create_collection(persist_dir, _COLLECTION_NAME, fn)
    elif not force_reingest and collection.count() > 0:
        logger.info(
            "NyayaSathi Chroma collection already has %d chunks — skipping ingestion. "
            "Set force_reingest=True to re-ingest.",
            collection.count(),
        )
        return collection.count()

    today = date.today().isoformat()
    total_chunks = 0
    skipped_pdfs = 0

    for pdf in pdfs:
        meta = load_sidecar(pdf)
        if meta is None:
            skipped_pdfs += 1
            continue

        logger.info("Ingesting legal document '%s' …", pdf.name)
        try:
            raw = extract_text_from_pdf(pdf)
        except Exception as exc:
            logger.error("Failed to extract text from '%s': %s — skipping.", pdf.name, exc)
            skipped_pdfs += 1
            continue

        clean = clean_text(raw)
        chunks = chunk_text(clean)
        if not chunks:
            logger.warning("'%s' produced no text chunks — skipping.", pdf.name)
            continue

        jurisdiction = str(meta.get("jurisdiction", "central")).strip().lower()
        if jurisdiction not in ("central", "state"):
            jurisdiction = "central"
        applicable_state = str(meta.get("applicable_state", "") or "").strip()

        doc_title = meta.get("document_title") or meta.get("source_title") or pdf.stem
        authority = meta.get("issuing_authority") or meta.get("publisher") or ""
        pub_date = meta.get("publication_date") or meta.get("published_date") or ""

        ids = [f"{pdf.stem}__{i}" for i in range(len(chunks))]
        chunk_meta = [
            {
                # Common fields for RetrievalService / Source
                "source_title": doc_title,
                "publisher": authority,
                "url": str(meta.get("url", "") or ""),
                "topic": str(meta.get("topic") or meta.get("act_name") or ""),
                "language": str(meta.get("language", "en") or "en"),
                "published_date": str(pub_date or ""),
                "retrieval_date": str(meta.get("retrieval_date") or today),
                "region": applicable_state or "India",
                # §5.3 legal fields
                "document_title": doc_title,
                "issuing_authority": authority,
                "jurisdiction": jurisdiction,
                "applicable_state": applicable_state,
                "applicable_state_lower": applicable_state.lower(),
                "act_name": str(meta.get("act_name", "") or ""),
                "section_number": str(meta.get("section_number", "") or ""),
                "publication_date": str(pub_date or ""),
                "effective_date": str(meta.get("effective_date", "") or ""),
                "last_updated_date": str(meta.get("last_updated_date", "") or ""),
                "source_file": pdf.name,
            }
            for _ in chunks
        ]

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
        logger.warning("%d legal PDF(s) skipped (missing sidecar or extraction error).", skipped_pdfs)
    logger.info("NyayaSathi ingestion complete: %d total chunks in collection.", total_chunks)
    return total_chunks


@lru_cache(maxsize=1)
def get_nyayasathi_collection(persist_dir: str, embedding_service_id: int):
    """Return the NyayaSathi Chroma collection (cached singleton)."""
    from app.services.embedding_service import get_embedding_service

    svc = get_embedding_service()
    fn = chroma_embedding_fn(svc)
    _client, collection = get_or_create_collection(persist_dir, _COLLECTION_NAME, fn)
    return collection
