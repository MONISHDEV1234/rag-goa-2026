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
    return JSONResponse({
        "status": "ok",
        "mode": "skeleton",
        "endpoints": ["/api/query", "/api/voice"],
    })


# Explicit root → landing page
@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import FileResponse
    return FileResponse(str(_frontend_dir / "landing.html"))


# /app → main voice RAG UI
@app.get("/app", include_in_schema=False)
async def app_page():
    from fastapi.responses import FileResponse
    return FileResponse(str(_frontend_dir / "index.html"))


# ---------------------------------------------------------------------------
# Serve all other static assets (js, css, icons, sw.js, manifest.json…)
# ---------------------------------------------------------------------------

_frontend_dir = Path(__file__).parent.parent / "frontend"

if _frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="frontend",
    )
