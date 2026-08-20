"""
app.stt — Speech-to-Text package (Role 2)

Public interface:
    transcribe(audio_bytes: bytes) -> str
"""

from .sarvam_client import transcribe

__all__ = ["transcribe"]
