"""
Mock retriever — Role 1 integration stub.

THIS FILE IS A PLACEHOLDER.
Replace this import in app/rag/orchestrator.py when Role 1's retrieve_context() is ready:

  # Before (mock):
  from app.retrieval.mock_retriever import retrieve_context

  # After (real Role 1):
  from app.retrieval.retriever import retrieve_context

The interface contract is unchanged:
  async def retrieve_context(query: str, top_k: int = 3) -> list[DocumentChunk]

The mock returns plausible-looking fake chunks so the orchestrator, guardrails,
and tests can run end-to-end without Role 1 being implemented.
"""

from __future__ import annotations

from app.schemas import DocumentChunk

# Sample MSMARCO-XI style passages for mock returns
_MOCK_PASSAGES = [
    DocumentChunk(
        text=(
            "The AI4Bharat MSMARCO-XI dataset is a multilingual question answering "
            "benchmark derived from the MS MARCO dataset, extended to cover multiple "
            "Indian languages including Hindi, Bengali, Tamil, Telugu, and more."
        ),
        doc_id="msmarco_xi_001",
        chunk_strategy="semantic",
        similarity_score=0.91,
    ),
    DocumentChunk(
        text=(
            "MS MARCO (Microsoft Machine Reading Comprehension) contains real Bing "
            "search queries paired with passages extracted from web documents and "
            "human-generated answers for reading comprehension tasks."
        ),
        doc_id="msmarco_xi_002",
        chunk_strategy="sliding_window",
        similarity_score=0.84,
    ),
    DocumentChunk(
        text=(
            "Multilingual information retrieval systems require embeddings that are "
            "semantically aligned across languages. FastEmbed with BGE-small provides "
            "a local, low-latency option suitable for deployment without external APIs."
        ),
        doc_id="msmarco_xi_003",
        chunk_strategy="semantic",
        similarity_score=0.78,
    ),
]


async def retrieve_context(query: str, top_k: int = 3) -> list[DocumentChunk]:
    """
    MOCK IMPLEMENTATION — returns static chunks regardless of query.

    Replace with Role 1's real implementation.
    Interface is identical to what Role 1 will expose.
    """
    # Return top_k slices of mock data
    return _MOCK_PASSAGES[:top_k]
