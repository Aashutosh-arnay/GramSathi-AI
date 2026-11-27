"""Embedding service – provider abstraction.

Supported providers (selected via EMBEDDING_PROVIDER env var):

* ``local`` (default): uses ``sentence-transformers`` with a multilingual
  model so Hindi queries match English documents without a remote key.

Additional providers can be registered by adding an entry to
``_PROVIDER_REGISTRY`` and implementing the ``EmbeddingService`` protocol.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Protocol, runtime_checkable

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@runtime_checkable
class EmbeddingService(Protocol):
    """Minimal interface every embedding backend must satisfy."""

    def embed_query(self, text: str) -> list[float]:
        """Return a single embedding vector for *text*."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per document in *texts*."""
        ...

    @property
    def dimension(self) -> int:
        """Embedding dimension (number of floats per vector)."""
        ...


# ---------------------------------------------------------------------------
# Local (sentence-transformers) provider
# ---------------------------------------------------------------------------


class LocalEmbeddingService:
    """Wraps a ``sentence-transformers`` model for offline, key-free use.

    The multilingual model ``paraphrase-multilingual-MiniLM-L12-v2`` handles
    Hindi and English in a shared embedding space so a Hindi query retrieves
    English documents (and vice-versa) without translation.
    """

    def __init__(self, model_name: str) -> None:
        import os
        import sys

        if sys.platform == "win32":
            scripts_dir = os.path.join(sys.prefix, "Scripts")
            if os.path.isdir(scripts_dir):
                os.add_dll_directory(scripts_dir)

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from exc

        logger.info("Loading embedding model '%s' …", model_name)
        self._model = SentenceTransformer(model_name)
        self._dim: int = self._model.get_sentence_embedding_dimension()
        logger.info("Embedding model loaded (dim=%d).", self._dim)

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    @property
    def dimension(self) -> int:
        return self._dim


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return a singleton embedding service selected by EMBEDDING_PROVIDER."""
    settings = get_settings()
    provider = (settings.embedding_provider or "local").lower()

    if provider == "local":
        model = settings.embedding_model or "paraphrase-multilingual-MiniLM-L12-v2"
        return LocalEmbeddingService(model)

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER='{provider}'. Supported: 'local'."
    )
