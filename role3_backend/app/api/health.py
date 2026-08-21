"""Health endpoint — GET /health"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Liveness probe.
    Role 2 frontend polls this to show the 'System Ready' indicator.
    """
    return HealthResponse(status="ok", service="role3-rag-backend")
