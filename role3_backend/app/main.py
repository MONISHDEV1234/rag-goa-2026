"""
FastAPI application entry point.

Startup order:
  1. Load settings from .env
  2. Pre-warm the retriever (Role 1 drop-in) on startup
  3. Mount API routers
  4. Serve

CORS is configured permissively for the hackathon demo.
Tighten allow_origins in production.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Add any startup/shutdown logic here (e.g., loading the FAISS index).
    Role 1 will provide a load_index() call that goes here.
    """
    # -----------------------------------------------------------------
    # ROLE 1 INTEGRATION POINT:
    # Uncomment and replace with Role 1's actual index loader once ready.
    #
    # from app.retrieval.retriever import load_index
    # await load_index()
    # -----------------------------------------------------------------
    print("[Role 3] Backend starting up — RAG pipeline ready.")
    yield
    print("[Role 3] Backend shutting down.")


app = FastAPI(
    title="HH Goa 2026 — Voice RAG Backend (Role 3)",
    description=(
        "FastAPI backend powering the Voice-Enabled RAG system. "
        "Provides /api/query (text) and /api/voice (audio) endpoints."
    ),
    version="0.1.0",
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
