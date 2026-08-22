"""
API routes — thin layer that delegates all work to the RAG orchestrator.

Routes:
  POST /api/query  — text query path
  POST /api/voice  — voice (base64 audio) path

Routes do NOT contain pipeline logic.
All business logic lives in app/rag/orchestrator.py.
"""

import base64
import binascii

from fastapi import APIRouter, HTTPException, status

from app.schemas import QueryRequest, VoiceRequest, RAGResponse
from app.rag.orchestrator import RAGService

router = APIRouter(tags=["rag"])
_rag_service = RAGService()


@router.post(
    "/query",
    response_model=RAGResponse,
    summary="Text query endpoint",
    description="Submit a text query and receive a grounded RAG answer.",
)
async def query(request: QueryRequest) -> RAGResponse:
    """
    Text path:
      query string → Input Guard → Retrieval → Context Guard → Groq → Grounding → RAGResponse
    """
    try:
        return await _rag_service.run(transcript=request.query, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {exc}",
        ) from exc


@router.post(
    "/voice",
    response_model=RAGResponse,
    summary="Voice query endpoint",
    description="Submit base64-encoded audio. Backend transcribes via Sarvam STT then runs the RAG pipeline.",
)
async def voice(request: VoiceRequest) -> RAGResponse:
    """
    Voice path:
      base64 audio → decode → STT → transcript → RAG pipeline → RAGResponse

    Audio format: base64-encoded bytes.
    Content type hint is passed to the STT client (default: audio/webm).
    """
    try:
        audio_bytes = base64.b64decode(request.audio_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 audio payload: {exc}",
        ) from exc

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio payload is empty.",
        )

    try:
        return await _rag_service.run_voice(
            audio_bytes=audio_bytes,
            content_type=request.content_type,
            top_k=request.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice RAG pipeline error: {exc}",
        ) from exc
