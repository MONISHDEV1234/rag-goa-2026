"""
app/api/routes.py — API route skeleton (mock responses)

POST /api/query  — text query → mock RAGResponse
POST /api/voice  — audio upload → mock RAGResponse

Replace the mock logic here with real RAG calls once
Role 1 (retrieval) and the LLM harness are wired up.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.schemas import DocumentChunk, RAGResponse

router = APIRouter(prefix="/api", tags=["rag"])

# ---------------------------------------------------------------------------
# Mock data bank — realistic demo responses
# ---------------------------------------------------------------------------

_MOCK_QA = [
    {
        "keywords": ["retrieval", "rag", "augmented"],
        "transcript": "What is retrieval augmented generation?",
        "answer": (
            "Retrieval-Augmented Generation (RAG) combines a retrieval system with a "
            "generative language model. Instead of relying solely on parametric knowledge, "
            "RAG first retrieves relevant passages from an external knowledge base (such as "
            "MSMARCO-XI via FAISS), then conditions the LLM generation on those passages. "
            "This reduces hallucinations and ensures the answer is grounded in verifiable documents."
        ),
        "sources": [
            {"doc_id": "msmarco-xi-doc-00412", "chunk_strategy": "semantic",  "similarity_score": 0.921},
            {"doc_id": "msmarco-xi-doc-01876", "chunk_strategy": "sliding",   "similarity_score": 0.887},
            {"doc_id": "msmarco-xi-doc-03201", "chunk_strategy": "semantic",  "similarity_score": 0.812},
        ],
        "latency": {"stt": 58, "embedding": 9, "retrieval": 5, "generation": 74, "grounding": 4},
        "is_grounded": True,
    },
    {
        "keywords": ["transformer", "attention", "architecture"],
        "transcript": "How does the transformer architecture work?",
        "answer": (
            "The Transformer architecture relies entirely on self-attention mechanisms. "
            "Each token attends to every other token through multi-head attention computed as "
            "softmax(QKᵀ/√dₖ)V. This allows parallel processing and captures long-range "
            "dependencies efficiently. Decoder-only variants (like GPT) are used for generation."
        ),
        "sources": [
            {"doc_id": "msmarco-xi-doc-00891", "chunk_strategy": "semantic",  "similarity_score": 0.944},
            {"doc_id": "msmarco-xi-doc-02114", "chunk_strategy": "semantic",  "similarity_score": 0.903},
        ],
        "latency": {"stt": 61, "embedding": 8, "retrieval": 4, "generation": 81, "grounding": 3},
        "is_grounded": True,
    },
    {
        "keywords": ["faiss", "vector", "search", "index"],
        "transcript": "How does in-memory vector search with FAISS work?",
        "answer": (
            "FAISS (Facebook AI Similarity Search) stores document chunk embeddings in a "
            "IndexFlatIP index loaded entirely into RAM at startup. At query time, the query "
            "is embedded (~9 ms) and FAISS performs an exact inner-product search (~5 ms) to "
            "return top-K passages without any disk I/O, enabling sub-200 ms end-to-end latency."
        ),
        "sources": [
            {"doc_id": "msmarco-xi-doc-04532", "chunk_strategy": "sliding",   "similarity_score": 0.912},
            {"doc_id": "msmarco-xi-doc-01234", "chunk_strategy": "metadata",  "similarity_score": 0.878},
            {"doc_id": "msmarco-xi-doc-03891", "chunk_strategy": "semantic",  "similarity_score": 0.843},
        ],
        "latency": {"stt": 54, "embedding": 11, "retrieval": 6, "generation": 68, "grounding": 5},
        "is_grounded": True,
    },
    {
        "keywords": ["chunk", "semantic", "sliding"],
        "transcript": "What is semantic chunking?",
        "answer": (
            "Semantic chunking splits documents at natural meaning boundaries detected by "
            "measuring cosine similarity drops between adjacent sentence embeddings. "
            "This keeps related ideas together. Sliding-window chunking uses fixed-size "
            "overlapping windows regardless of content. Semantic chunking gives better retrieval "
            "quality; sliding-window is faster to compute during offline indexing."
        ),
        "sources": [
            {"doc_id": "msmarco-xi-doc-02977", "chunk_strategy": "semantic",  "similarity_score": 0.931},
            {"doc_id": "msmarco-xi-doc-04102", "chunk_strategy": "sliding",   "similarity_score": 0.891},
        ],
        "latency": {"stt": 63, "embedding": 10, "retrieval": 5, "generation": 79, "grounding": 4},
        "is_grounded": True,
    },
    {
        "keywords": ["latency", "200ms", "fast", "performance", "speed"],
        "transcript": "How does the system achieve under 200 ms latency?",
        "answer": (
            "Sub-200 ms is achieved through: FAISS loaded in RAM (zero disk I/O per request), "
            "FastEmbed BGE-small-en-v1.5 pre-warmed (~9 ms embedding), Groq llama-3.1-8b-instant "
            "generating in ~70 ms, single async event loop with httpx connection pooling, "
            "prompts capped at 512 tokens, and max output at 256 tokens. "
            "Budget: STT ~60 ms + Embedding ~10 ms + FAISS ~5 ms + LLM ~75 ms + Grounding ~5 ms = ~155 ms."
        ),
        "sources": [
            {"doc_id": "msmarco-xi-doc-03341", "chunk_strategy": "semantic",  "similarity_score": 0.956},
            {"doc_id": "msmarco-xi-doc-04812", "chunk_strategy": "metadata",  "similarity_score": 0.902},
            {"doc_id": "msmarco-xi-doc-02256", "chunk_strategy": "sliding",   "similarity_score": 0.871},
        ],
        "latency": {"stt": 55, "embedding": 8, "retrieval": 4, "generation": 71, "grounding": 4},
        "is_grounded": True,
    },
]

_REFUSAL_RESPONSE = {
    "transcript": "",
    "answer": (
        "I couldn't find enough information in the provided knowledge base to answer that question. "
        "Please try asking about RAG, transformers, FAISS, chunking, or system latency."
    ),
    "sources": [],
    "latency": {"stt": 55, "embedding": 9, "retrieval": 4, "generation": 0, "grounding": 2},
    "is_grounded": False,
}


def _jitter(ms: int) -> int:
    """Add ±12% realistic timing jitter."""
    return round(ms * (0.88 + random.random() * 0.24))


def _build_response(query: str, transcript: str | None = None) -> RAGResponse:
    """
    Pick a mock QA pair matching the query, or return a refusal.
    TODO: Replace with real RAG pipeline calls.
    """
    q_lower = query.lower()
    match = next(
        (qa for qa in _MOCK_QA if any(kw in q_lower for kw in qa["keywords"])),
        None,
    )
    raw = match or _REFUSAL_RESPONSE

    latency = {k: _jitter(v) for k, v in raw["latency"].items()}
    latency["total"] = sum(latency.values())

    sources = [
        DocumentChunk(
            text=f"Retrieved passage from {s['doc_id']} using {s['chunk_strategy']} strategy.",
            doc_id=s["doc_id"],
            chunk_strategy=s["chunk_strategy"],
            similarity_score=round(s["similarity_score"] * (0.95 + random.random() * 0.05), 3),
        )
        for s in raw["sources"]
    ]

    return RAGResponse(
        transcript=transcript or raw["transcript"] or query,
        answer=raw["answer"],
        is_grounded=raw["is_grounded"],
        retrieved_sources=sources,
        latency_breakdown=latency,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3


@router.post("/query", response_model=RAGResponse, summary="Text RAG query")
async def text_query(body: QueryRequest) -> RAGResponse:
    """
    Accept a JSON text query and return a mock RAGResponse.

    TODO (Role 3): Replace with real pipeline:
        chunks = await retrieve_context(body.query, top_k=body.top_k)
        return await run_rag(body.query, chunks)
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query field is required")

    # Simulate processing time (remove when using real pipeline)
    await asyncio.sleep(random.uniform(0.08, 0.16))

    return _build_response(query)


@router.post("/voice", response_model=RAGResponse, summary="Voice RAG query")
async def voice_query(audio: UploadFile = File(...)) -> RAGResponse:
    """
    Accept a multipart audio upload, run STT, then RAG.

    TODO (Role 3): Replace with:
        audio_bytes = await audio.read()
        transcript = await transcribe(audio_bytes, audio.content_type)
        chunks = await retrieve_context(transcript, top_k=3)
        return await run_rag(transcript, chunks)
    """
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        # Accept any file in skeleton mode — real version validates content_type
        pass

    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=422, detail="Audio file too small or empty.")

    # Simulate STT + pipeline latency
    await asyncio.sleep(random.uniform(0.13, 0.22))

    # In the skeleton, pick a random QA pair since we have no real transcript
    mock_qa = random.choice(_MOCK_QA)
    return _build_response(
        query=mock_qa["transcript"],
        transcript=mock_qa["transcript"],
    )
