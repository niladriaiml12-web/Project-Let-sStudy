"""
app/config.py

Central configuration management using Pydantic Settings.
All values are loaded from environment variables / .env file.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses .env file in the project root for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Google / Gemini
    # -------------------------------------------------------------------------
    gemini_api_key: str = Field(..., description="Google Gemini API key")

    # -------------------------------------------------------------------------
    # LLM / Model Configuration
    # -------------------------------------------------------------------------
    llm_provider: str = Field(default="gemini", description="LLM provider: gemini | openai | ollama")
    llm_model: str = Field(default="gemini-3.5-flash", description="Model name for text generation")
    vision_model: str = Field(default="gemini-3.5-flash", description="Model name for OCR/Vision tasks")
    embedding_model: str = Field(
        default="gemini-embedding-001",
        description="Google embedding model identifier",
    )

    # -------------------------------------------------------------------------
    # ChromaDB
    # -------------------------------------------------------------------------
    chroma_persist_dir: str = Field(
        default="./data/chroma_store",
        description="Local path for ChromaDB persistent storage",
    )

    # -------------------------------------------------------------------------
    # File Storage
    # -------------------------------------------------------------------------
    upload_dir: str = Field(default="./data/uploads", description="Temp directory for uploaded files")
    max_upload_size_mb: int = Field(default=50, description="Maximum upload size in megabytes")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/study_rag.db",
        description="SQLAlchemy async database URL",
    )

    # -------------------------------------------------------------------------
    # API Security (Tenant API Keys)
    # -------------------------------------------------------------------------
    valid_api_keys: str = Field(
        default="dev-key-cse-aiml-2026,dev-key-cse-core-2026",
        description="Comma-separated list of valid API keys",
    )

    @property
    def api_key_set(self) -> set:
        """Returns valid API keys as a set for O(1) lookup."""
        return {k.strip() for k in self.valid_api_keys.split(",") if k.strip()}

    # -------------------------------------------------------------------------
    # RAG Configuration
    # -------------------------------------------------------------------------
    rag_top_k: int = Field(default=5, description="Number of chunks to retrieve per query")
    rag_chunk_size: int = Field(default=512, description="Characters per text chunk")
    rag_chunk_overlap: int = Field(default=64, description="Character overlap between chunks")

    # -------------------------------------------------------------------------
    # App
    # -------------------------------------------------------------------------
    app_env: str = Field(default="development", description="development | production")
    log_level: str = Field(default="INFO", description="Logging level")

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns the cached Settings singleton.
    Use this in FastAPI Depends() to inject config.
    """
    settings = Settings()
    settings.ensure_dirs()
    return settings
