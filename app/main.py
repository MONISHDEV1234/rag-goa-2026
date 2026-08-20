"""
app/main.py — FastAPI application entry point

Role 2 created this skeleton. Role 3 expands it with full RAG orchestration.
Currently wired with MOCK routes that return realistic fake responses
so the frontend can be tested end-to-end before the real pipeline is ready.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.stt.sarvam_client import close_client
from app.api.routes import router as api_router


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────────────────────────────
    # TODO (Role 1): load FAISS index + metadata here
    # TODO (Role 3): warm FastEmbed embedding model here
    print("✓ App startup complete (skeleton mode — mock responses active)")
    yield
    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    await close_client()   # close Sarvam httpx client


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HH Goa 2026 — Voice RAG",
    description=(
        "Voice-Enabled Retrieval-Augmented Generation system for HH Goa 2026 Task 2. "
        "Currently running in skeleton mode with mock responses."
    ),
    version="0.1.0-skeleton",
    lifespan=lifespan,
)

# CORS — allow all origins in dev; tighten before final submission
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routes (mock skeleton)
# ---------------------------------------------------------------------------

app.include_router(api_router)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health():
    """
    Health check. Returns system readiness.
    TODO (Role 3): extend to report FAISS index status, model load status.
    """
    return JSONResponse({
        "status": "ok",
        "mode": "skeleton",  # change to "live" when real pipeline is wired
        "endpoints": ["/api/query", "/api/voice"],
    })


# ---------------------------------------------------------------------------
# Serve frontend — MUST be last (catches all unmatched routes)
# ---------------------------------------------------------------------------

_frontend_dir = Path(__file__).parent.parent / "frontend"

if _frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="frontend",
    )
