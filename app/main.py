"""
app/main.py — FastAPI application entry point (SONAR)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.stt.sarvam_client import close_client
from app.api.routes import router as api_router

# Resolve frontend directory once at module load
_frontend_dir = Path(__file__).parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✓ SONAR startup complete (skeleton mode)")
    yield
    await close_client()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SONAR — SOund Neural Answer Retrieval",
    version="0.1.0-skeleton",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

app.include_router(api_router)

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health():
    return JSONResponse({"status": "ok", "mode": "skeleton"})

# ---------------------------------------------------------------------------
# Page routes  (must come BEFORE StaticFiles mount)
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def landing():
    """Serve SONAR landing page."""
    return FileResponse(str(_frontend_dir / "landing.html"))

@app.get("/app", include_in_schema=False)
async def app_page():
    """Serve SONAR voice RAG app."""
    return FileResponse(str(_frontend_dir / "index.html"))

# ---------------------------------------------------------------------------
# Static assets — mounted at /static so it doesn't shadow page routes
# ---------------------------------------------------------------------------

if _frontend_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(_frontend_dir)),
        name="static",
    )
