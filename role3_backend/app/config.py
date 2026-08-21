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

    # --- Retrieval (Role 1 FAISS) ---
    retrieval_top_k: int = 3
    # Path to the pre-built FAISS index directory (output of embed_index.py).
    # Override in .env when the index lives at a non-default location.
    faiss_index_dir: str = "data/index"
    # Similarity threshold below which we issue a missing-context refusal.
    # 0.35 is a reasonable default for intfloat/multilingual-e5-large on MSMARCO-XI
    # (inner-product scores post L2-normalize). Tune experimentally with evaluate.py.
    # Must be > 0.20 so the test suite's score=0.20 "low context" fixtures work correctly.
    context_similarity_threshold: float = 0.35
    # Anti-hallucination pre-filter: chunks with score below this are dropped
    # before the LLM sees them. 0.0 = disabled (threshold guard handles it instead).
    retrieval_min_score: float = 0.0

    # --- Reliability ---
    max_retries: int = 3  # Tenacity max attempts on transient Groq errors


# Singleton — import `settings` everywhere
settings = Settings()
