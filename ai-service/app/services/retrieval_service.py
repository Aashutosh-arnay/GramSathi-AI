"""Retrieval service – semantic search over a Chroma vector store.

This module is intentionally vector-store-agnostic: it talks to Chroma
through a thin wrapper so a different store can be dropped in later.

Threshold behaviour
-------------------
If the best matching chunk scores below ``retrieval_threshold`` (cosine
similarity), the service returns an empty list.  The caller (FarmSathi
service) must then return ``answerStatus = insufficient_information`` and
MUST NOT call the LLM.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RetrievedChunk:
    """A single chunk returned by semantic search."""

    text: str
    score: float  # cosine similarity [0.0–1.0]

    # Common metadata – may be empty/None when absent
    source_title: str = ""
    publisher: str = ""
    url: str = ""
    topic: str = ""
    language: str = "en"
    published_date: str | None = None   # ISO-8601 string or None
    retrieval_date: str | None = None   # ISO-8601 string or None
    region: str | None = None
    # Full raw metadata dict for domain-specific fields (e.g. NyayaSathi §5.3)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Retrieval service
# ---------------------------------------------------------------------------


class RetrievalService:
    """Wraps a Chroma collection and exposes a single ``search`` method."""

    def __init__(
        self,
        collection,          # chromadb.Collection
        threshold: float,
        top_k: int,
    ) -> None:
        self._collection = collection
        self._threshold = threshold
        self._top_k = top_k

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Return up to *top_k* chunks whose cosine similarity ≥ threshold.

        Optionally filters Chroma documents using a ``where`` metadata filter.
        Returns an empty list when nothing passes the threshold, signalling
        that the LLM should NOT be called.
        """
        k = top_k if top_k is not None else self._top_k
        count = self._collection.count()
        if count == 0:
            return []

        query_kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": min(k, count),
            "include": ["documents", "distances", "metadatas"],
        }
        if where:
            query_kwargs["where"] = where

        try:
            results = self._collection.query(**query_kwargs)
        except Exception as exc:
            logger.warning("Chroma query failed: %s", exc)
            return []

        documents: list[str] = results["documents"][0]
        distances: list[float] = results["distances"][0]
        metadatas: list[dict] = results["metadatas"][0]

        chunks: list[RetrievedChunk] = []
        for doc, dist, meta in zip(documents, distances, metadatas):
            # Chroma with cosine metric returns distance = 1 - similarity
            similarity = 1.0 - dist
            if similarity < self._threshold:
                logger.debug(
                    "Chunk below threshold (%.3f < %.3f), skipping.",
                    similarity,
                    self._threshold,
                )
                continue
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    score=similarity,
                    source_title=meta.get("source_title") or meta.get("document_title", ""),
                    publisher=meta.get("publisher") or meta.get("issuing_authority", ""),
                    url=meta.get("url", ""),
                    topic=meta.get("topic", ""),
                    language=meta.get("language", "en"),
                    published_date=meta.get("published_date") or meta.get("publication_date"),
                    retrieval_date=meta.get("retrieval_date"),
                    region=meta.get("region") or meta.get("applicable_state"),
                    metadata=dict(meta),
                )
            )

        logger.info(
            "search('%s…') → %d/%d chunks above threshold %.2f",
            query[:40],
            len(chunks),
            len(documents),
            self._threshold,
        )
        return chunks
