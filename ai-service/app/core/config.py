"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment (development | production)
    env: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Internal API key (AI_SERVICE_API_KEY header)
    ai_service_api_key: str = ""

    # LLM provider: "mock" (default) | "gemini"
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = ""

    # Embedding provider: "local" (default, sentence-transformers) | future cloud
    embedding_provider: str = "local"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # Vector store
    vector_store_type: str = "chroma"
    # Chroma persistence directory, relative to ai-service/
    chroma_persist_dir: str = "data/chroma"

    # Retrieval settings
    retrieval_top_k: int = 5
    # Cosine similarity threshold [0.0–1.0]; chunks below this score are dropped
    retrieval_threshold: float = 0.45

    # Data paths
    farmsathi_data_path: str = "../dataset/farmsathi"
    nyayasathi_data_path: str = "../dataset/nyayasathi"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

