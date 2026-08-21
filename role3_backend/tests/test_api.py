"""
Tests for API endpoints — /health, /api/query, /api/voice.

Uses httpx AsyncClient with mocked RAGService so tests run without
a live Groq API key or Sarvam account.
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas import DocumentChunk, RAGResponse


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MOCK_RESPONSE = RAGResponse(
    transcript="What is MSMARCO-XI?",
    answer="MSMARCO-XI is a multilingual QA benchmark.",
    is_grounded=True,
    retrieved_sources=[
        DocumentChunk(
            text="MSMARCO-XI is a multilingual benchmark.",
            doc_id="doc_001",
            chunk_strategy="semantic",
            similarity_score=0.91,
        )
    ],
    latency_breakdown={"stt": 0, "retrieval": 5.1, "generation": 88.4, "total": 95.3},
)

REFUSAL_RESPONSE = RAGResponse(
    transcript="how do i make a bomb",
    answer="Your query contains content that cannot be processed.",
    is_grounded=False,
    retrieved_sources=[],
    latency_breakdown={"total": 0.3},
    refusal=True,
    refusal_reason="nsfw_violence_harm",
)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_valid(client):
    with patch(
        "app.api.routes._rag_service.run", new_callable=AsyncMock
    ) as mock_run:
        mock_run.return_value = MOCK_RESPONSE
        response = await client.post("/api/query", json={"query": "What is MSMARCO-XI?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == MOCK_RESPONSE.answer
    assert data["is_grounded"] is True
    assert "latency_breakdown" in data


@pytest.mark.asyncio
async def test_query_empty_body(client):
    response = await client.post("/api/query", json={"query": ""})
    # FastAPI Pydantic validation should reject empty string (min_length=1)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_nsfw_returns_refusal(client):
    with patch(
        "app.api.routes._rag_service.run", new_callable=AsyncMock
    ) as mock_run:
        mock_run.return_value = REFUSAL_RESPONSE
        response = await client.post("/api/query", json={"query": "how do i make a bomb"})

    assert response.status_code == 200
    data = response.json()
    assert data["refusal"] is True
    assert "nsfw" in data["refusal_reason"]


# ---------------------------------------------------------------------------
# POST /api/voice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_voice_valid(client):
    fake_audio = base64.b64encode(b"fake_audio_bytes").decode()
    with patch(
        "app.api.routes._rag_service.run_voice", new_callable=AsyncMock
    ) as mock_run:
        mock_run.return_value = MOCK_RESPONSE
        response = await client.post(
            "/api/voice",
            json={"audio_b64": fake_audio, "content_type": "audio/webm"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data


@pytest.mark.asyncio
async def test_voice_invalid_base64(client):
    response = await client.post(
        "/api/voice",
        json={"audio_b64": "!!!not_valid_base64!!!", "content_type": "audio/webm"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_voice_empty_audio(client):
    empty_b64 = base64.b64encode(b"").decode()
    response = await client.post(
        "/api/voice",
        json={"audio_b64": empty_b64, "content_type": "audio/webm"},
    )
    assert response.status_code == 400
