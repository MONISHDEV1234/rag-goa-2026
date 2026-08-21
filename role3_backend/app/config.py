"""
Application configuration loaded from environment variables.
Uses pydantic-settings so values can come from .env or the process environment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Groq LLM ---
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"  # Override in .env to swap models instantly

    # --- Sarvam STT ---
    sarvam_api_key: str = ""

    # --- Retrieval ---
    retrieval_top_k: int = 3
    # Similarity threshold below which we issue a missing-context refusal.
    # Tune this value experimentally once the real FAISS index is loaded.
    context_similarity_threshold: float = 0.50

    # --- Reliability ---
    max_retries: int = 3  # Tenacity max attempts on transient Groq errors


# Singleton — import `settings` everywhere
settings = Settings()
