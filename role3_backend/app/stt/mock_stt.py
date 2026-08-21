"""
Mock STT client — Role 2 integration stub.

THIS FILE IS A PLACEHOLDER.
Replace this import in app/rag/orchestrator.py when Role 2's Sarvam client is ready:

  # Before (mock):
  from app.stt.mock_stt import transcribe

  # After (real Role 2 Sarvam client):
  from app.stt.sarvam import transcribe

Interface contract:
  async def transcribe(audio_bytes: bytes, content_type: str) -> str

The mock echoes a fixed transcript so the voice pipeline can be exercised
end-to-end without a live Sarvam API key.
"""

from __future__ import annotations

_MOCK_TRANSCRIPT = "What is the MSMARCO-XI dataset and how is it used for multilingual retrieval?"


async def transcribe(audio_bytes: bytes, content_type: str) -> str:
    """
    MOCK IMPLEMENTATION — ignores audio and returns a fixed transcript.

    Replace with Role 2's real Sarvam STT implementation.
    Interface is identical to what Role 2 will expose.
    """
    if not audio_bytes:
        raise ValueError("Empty audio bytes received by mock STT.")
    return _MOCK_TRANSCRIPT
