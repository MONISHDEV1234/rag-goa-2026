"""
app/main.py — FastAPI application entry point (Role 3 owns this file)

Role 2 created the minimal skeleton so the frontend can be served
and the app can run on Replit/deployment targets.
Role 3 must expand this with full RAG orchestration, routes, and startup logic.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.stt.sarvam_client import close_client


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    # Role 3: load FAISS index, embedding model, Groq client here
    yield
    # SHUTDOWN
    await close_client()  # close Sarvam HTTP client


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HH Goa 2026 — Voice RAG",
    description="Voice-Enabled RAG system for HH Goa 2026 Task 2",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — restrict in production to your actual frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Role 3: tighten this before final submission
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoint (Role 3 should expand this to check model/index readiness)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# API routes placeholder — Role 3 registers real routes here
# ---------------------------------------------------------------------------

# Role 3: from app.api.routes import router; app.include_router(router, prefix="/api")


# ---------------------------------------------------------------------------
# Serve frontend — MUST be last (catches all unmatched routes)
# ---------------------------------------------------------------------------

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

app.mount(
    "/",
    StaticFiles(directory=_frontend_dir, html=True),
    name="frontend",
)
