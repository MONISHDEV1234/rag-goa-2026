"""
app/stt/audio.py — Audio validation and format utilities (Role 2)

Provides lightweight helpers that are called before bytes are sent to the
Sarvam AI API.  Kept as pure functions with no external dependencies so they
can be unit-tested without network access.
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# Sarvam AI accepts these MIME types for its speech-to-text endpoint
SUPPORTED_MIME_TYPES: set[str] = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/ogg",
    "audio/ogg;codecs=opus",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/mp3",
}

# Minimum audio size guard (< 1 KB is almost certainly silence or a corrupt blob)
MIN_AUDIO_BYTES = 1_024

# Maximum audio upload size we will accept before rejecting at the gateway
# (prevents accidental gigantic uploads; Sarvam has its own limit too)
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB


class AudioValidationError(ValueError):
    """Raised when audio bytes fail a pre-flight check."""


def validate_audio(audio_bytes: bytes, content_type: str | None = None) -> None:
    """
    Perform basic pre-flight checks on raw audio bytes.

    Args:
        audio_bytes:  Raw bytes from the multipart upload.
        content_type: MIME type reported by the browser (may be None).

    Raises:
        AudioValidationError: if any check fails.
    """
    if not audio_bytes:
        raise AudioValidationError("Audio payload is empty.")

    size = len(audio_bytes)

    if size < MIN_AUDIO_BYTES:
        raise AudioValidationError(
            f"Audio payload is too small ({size} bytes). "
            "This may indicate silence or a corrupt recording."
        )

    if size > MAX_AUDIO_BYTES:
        raise AudioValidationError(
            f"Audio payload is too large ({size / 1_048_576:.1f} MB). "
            f"Maximum accepted size is {MAX_AUDIO_BYTES // 1_048_576} MB."
        )

    if content_type is not None:
        # Normalise: strip whitespace, lower-case
        normalised = content_type.strip().lower()
        if not any(normalised.startswith(m) for m in SUPPORTED_MIME_TYPES):
            logger.warning(
                "Received audio with unrecognised MIME type %r — "
                "will attempt to forward to Sarvam anyway.",
                content_type,
            )


def audio_to_file_like(audio_bytes: bytes, filename: str = "audio.webm") -> io.BytesIO:
    """
    Wrap raw bytes in a named BytesIO object suitable for multipart upload.

    Args:
        audio_bytes: Raw audio bytes.
        filename:    Logical filename sent in the multipart Content-Disposition.

    Returns:
        BytesIO object with a `.name` attribute set.
    """
    buf = io.BytesIO(audio_bytes)
    buf.name = filename  # httpx/requests reads `.name` for the part filename
    return buf


def infer_extension(content_type: str | None) -> str:
    """
    Return a reasonable file extension for the given MIME type.

    Used when constructing the multipart filename so the Sarvam API
    can infer format without relying on the file header alone.
    """
    if content_type is None:
        return "webm"

    ct = content_type.strip().lower()
    if "ogg" in ct:
        return "ogg"
    if "wav" in ct:
        return "wav"
    if "mpeg" in ct or "mp3" in ct:
        return "mp3"
    if "mp4" in ct:
        return "mp4"
    # Default — browser MediaRecorder typically emits webm
    return "webm"
