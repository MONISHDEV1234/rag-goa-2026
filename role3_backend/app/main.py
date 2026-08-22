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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, routes

# Propagate environment variables from settings into os.environ
import os
if settings.sarvam_api_key and not os.environ.get("SARVAM_API_KEY"):
    os.environ["SARVAM_API_KEY"] = settings.sarvam_api_key
if settings.groq_api_key and not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = settings.groq_api_key

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
        index_dir = settings.resolved_faiss_index_dir
        logger.info(
            "[startup] Loading FAISS index from '%s' ...", index_dir
        )
        # init_retrieval is synchronous (disk I/O + ONNX model load).
        # Run it in a thread so we don't block the event loop during startup.
        await asyncio.to_thread(init_retrieval, index_dir)
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

# --- Frontend Pages & Static Files ---
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

@app.get("/", include_in_schema=False)
async def landing():
    return FileResponse(str(_frontend_dir / "landing.html"))

@app.get("/app", include_in_schema=False)
async def app_page():
    return FileResponse(str(_frontend_dir / "index.html"))

@app.get("/about", include_in_schema=False)
async def about_page():
    return FileResponse(str(_frontend_dir / "about.html"))

@app.get("/tutorial", include_in_schema=False)
async def tutorial_page():
    return FileResponse(str(_frontend_dir / "tutorial.html"))

if _frontend_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(_frontend_dir)),
        name="static",
    )
    # Also mount root static for scripts/styles referenced relatively
    app.mount(
        "/frontend",
        StaticFiles(directory=str(_frontend_dir)),
        name="frontend",
    )
    # Serve root assets directly (style.css, app.js, orb.js, manifest.json, sw.js, icon.svg, etc.)
    @app.get("/{filename:path}", include_in_schema=False)
    async def serve_root_asset(filename: str):
        file_path = _frontend_dir / filename
        if file_path.is_file():
            return FileResponse(str(file_path))
        raise HTTPException(status_code=404, detail="File not found")
