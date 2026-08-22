"""
Application configuration loaded from environment variables.
Uses pydantic-settings so values can come from .env or the process environment.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_project_root = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_project_root / ".env", ".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Groq LLM ---
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"  # Active model on Groq

    # --- Sarvam STT ---
    sarvam_api_key: str = ""

    # --- Retrieval (Role 1 FAISS) ---
    retrieval_top_k: int = 3
    # Path to the pre-built FAISS index directory (output of embed_index.py).
    # Override in .env when the index lives at a non-default location.
    faiss_index_dir: str = str(_project_root / "role1" / "data" / "index_minilm")

    @property
    def resolved_faiss_index_dir(self) -> str:
        p = Path(self.faiss_index_dir)
        if not p.is_absolute():
            candidate = _project_root / p
            if candidate.exists():
                return str(candidate)
        return str(p)

    # Similarity threshold below which we issue a missing-context refusal.
    # 0.20 is calibrated for paraphrase-multilingual-MiniLM-L12-v2 on MSMARCO-XI.
    # MiniLM inner-product scores (post L2-normalize) are lower than e5-large,
    # so a lower threshold avoids incorrectly refusing valid queries.
    # Tune experimentally with evaluate.py.
    context_similarity_threshold: float = 0.20
    # Anti-hallucination pre-filter: chunks with score below this are dropped
    # before the LLM sees them. 0.0 = disabled (threshold guard handles it instead).
    retrieval_min_score: float = 0.0

    # --- Reliability ---
    max_retries: int = 3  # Tenacity max attempts on transient Groq errors


# Singleton — import `settings` everywhere
settings = Settings()
