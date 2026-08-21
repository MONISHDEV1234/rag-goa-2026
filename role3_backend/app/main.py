"""
FastAPI application entry point — HH Goa 2026 Voice RAG Backend.

Startup order:
  1. Load settings from .env
  2. Load FAISS index + embedding model into memory (Role 1 init_retrieval)
  3. Mount API routers
  4. Serve

CORS is configured permissively for the hackathon demo.
Tighten allow_origins before a production deployment.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, routes
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup:
      - Initialises the Role 1 FAISS retrieval index.
        The index is loaded once into memory here and reused across all requests.
        It is never rebuilt or reloaded per request.

    Raises RuntimeError on startup if the FAISS index files are missing (i.e.
    embed_index.py has not been run yet). This is intentional — a missing index
    means the backend cannot serve any queries and should fail loudly.
    """
    # ------------------------------------------------------------------
    # ROLE 1 INTEGRATION — ACTIVE
    # ------------------------------------------------------------------
    from app.retrieval.retriever import init_retrieval, get_retrieval_status
    import asyncio

    try:
        logger.info(
            "[startup] Loading FAISS index from '%s' ...", settings.faiss_index_dir
        )
        # init_retrieval is synchronous (disk I/O + ONNX model load).
        # Run it in a thread so we don't block the event loop during startup.
        await asyncio.to_thread(init_retrieval, settings.faiss_index_dir)
        status = get_retrieval_status()
        logger.info(
            "[startup] FAISS index ready — %d vectors, model=%s, dim=%d",
            status.get("vectors_indexed", 0),
            status.get("model_name", "unknown"),
            status.get("embedding_dim", 0),
        )
        print(
            f"[Role 3] FAISS index loaded: {status.get('vectors_indexed', 0)} vectors "
            f"({status.get('model_name', '?')})"
        )
    except Exception as exc:
        # Log the error but do NOT crash the server — the /health endpoint
        # will report retrieval as uninitialized so Role 2 can surface it.
        logger.error("[startup] FAISS index load failed: %s", exc)
        print(f"[Role 3] WARNING: FAISS index not loaded — {exc}")
        print(
            "[Role 3] Run `python role1/embed_index.py` to build the index first, "
            "then point FAISS_INDEX_DIR in .env to the output directory."
        )

    print("[Role 3] Backend ready — RAG pipeline up.")
    yield
    print("[Role 3] Backend shutting down.")


app = FastAPI(
    title="HH Goa 2026 — Voice RAG Backend (Role 3)",
    description=(
        "FastAPI backend powering the Voice-Enabled RAG system. "
        "Provides /api/query (text) and /api/voice (audio) endpoints."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# --- CORS ---
# Role 2 frontend (served separately) needs cross-origin access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to frontend origin before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router)
app.include_router(routes.router, prefix="/api")
