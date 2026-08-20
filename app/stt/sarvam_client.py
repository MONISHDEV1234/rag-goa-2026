"""
app/stt/sarvam_client.py — Async Sarvam AI Speech-to-Text client (Role 2)

Public interface (as required by the shared project contract):

    async def transcribe(audio_bytes: bytes, content_type: str | None = None) -> str

Design decisions
----------------
* Single shared httpx.AsyncClient is created at module level and reused
  across requests to avoid connection-setup overhead on every call.
* Tenacity retries cover only transient failures (network errors, 429, 5xx).
* Validation and permanent errors (401, 400) are NOT retried.
* Latency of the STT call itself is NOT measured here — the caller
  (FastAPI route) stamps timestamps around this call so measurements
  are consistent across the pipeline.
* Never logs or stores the raw audio bytes.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .audio import AudioValidationError, audio_to_file_like, infer_extension, validate_audio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SARVAM_API_URL = "https://api.sarvam.ai/speech-to-text"

# Timeout in seconds.  STT is a network call so we set a generous-but-finite
# limit.  After this the request is treated as a transient failure and retried.
REQUEST_TIMEOUT_S = 15.0

# Maximum retries on transient failures (network, 429, 5xx)
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Shared async HTTP client
# ---------------------------------------------------------------------------
# Module-level client.  Reused across all requests for connection pooling.
# Closed gracefully on application shutdown via close_client().

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Return the shared async HTTP client, creating it on first call."""
    global _client
    if _client is None or _client.is_closed:
        api_key = _get_api_key()
        _client = httpx.AsyncClient(
            headers={
                "api-subscription-key": api_key,
            },
            timeout=httpx.Timeout(REQUEST_TIMEOUT_S),
            # Keep-alive for connection reuse
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        logger.debug("Sarvam HTTP client initialised.")
    return _client


async def close_client() -> None:
    """Gracefully close the shared HTTP client.  Call on application shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        logger.debug("Sarvam HTTP client closed.")
    _client = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    """Read the Sarvam API key from the environment.  Raises if missing."""
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "SARVAM_API_KEY environment variable is not set. "
            "Add it to your .env file."
        )
    return key


class SarvamSTTError(RuntimeError):
    """Raised for unrecoverable Sarvam API errors."""


class SarvamTransientError(IOError):
    """Raised for errors that are safe to retry (network, 429, 5xx)."""


def _raise_for_status(response: httpx.Response) -> None:
    """
    Translate HTTP error codes into typed exceptions.

    * 400, 401, 403, 422 → SarvamSTTError (do NOT retry)
    * 429, 5xx           → SarvamTransientError (safe to retry)
    * 200                → no-op
    """
    code = response.status_code
    if code == 200:
        return
    body: str = response.text[:500]  # truncate for logs
    if code in (400, 401, 403, 422):
        raise SarvamSTTError(
            f"Sarvam API returned non-retryable error {code}: {body}"
        )
    if code == 429 or code >= 500:
        raise SarvamTransientError(
            f"Sarvam API returned retryable error {code}: {body}"
        )
    # Any other unexpected code
    raise SarvamSTTError(f"Sarvam API returned unexpected status {code}: {body}")


def _parse_transcript(data: Any) -> str:
    """
    Extract the transcript string from the Sarvam API JSON response.

    Sarvam's speech-to-text endpoint returns:
        {
          "transcript": "...",
          ...
        }

    Returns empty string if the transcript field is blank (silence, etc.).
    """
    if not isinstance(data, dict):
        raise SarvamSTTError(
            f"Unexpected Sarvam response format (expected dict, got {type(data).__name__})"
        )
    transcript = data.get("transcript", "")
    if not isinstance(transcript, str):
        raise SarvamSTTError(
            f"Sarvam 'transcript' field is not a string: {transcript!r}"
        )
    return transcript.strip()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(SarvamTransientError),
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def _call_sarvam(audio_bytes: bytes, filename: str) -> str:
    """
    Make one (potentially retried) HTTP call to the Sarvam STT endpoint.

    Separated from `transcribe` so the retry decorator wraps only the
    network call, not the validation logic above it.
    """
    client = _get_client()
    file_obj = audio_to_file_like(audio_bytes, filename)
    model_name = os.environ.get("SARVAM_STT_MODEL", "saarika:v2.5")

    try:
        response = await client.post(
            SARVAM_API_URL,
            files={"file": (filename, file_obj, "audio/webm")},
            data={
                "model": model_name,
                "language_code": "en-IN",
            },
        )
    except httpx.TimeoutException as exc:
        raise SarvamTransientError(f"Sarvam request timed out: {exc}") from exc
    except httpx.NetworkError as exc:
        raise SarvamTransientError(f"Sarvam network error: {exc}") from exc

    _raise_for_status(response)
    return _parse_transcript(response.json())


async def transcribe(
    audio_bytes: bytes,
    content_type: str | None = None,
) -> str:
    """
    Convert raw audio bytes to a transcript string using Sarvam AI.

    This is the function that the rest of the application must call.
    It is the only public interface exported by the stt package.

    Args:
        audio_bytes:  Raw audio from the browser MediaRecorder.
        content_type: MIME type from the multipart Content-Type header
                      (used only to infer file extension; does not affect
                      whether the call proceeds).

    Returns:
        Transcribed text string.  May be empty if no speech was detected.

    Raises:
        AudioValidationError: audio is empty, too small, or too large.
        SarvamSTTError:       non-retryable provider error.
        SarvamTransientError: provider error that persisted past all retries.
    """
    # 1. Validate audio before touching the network
    validate_audio(audio_bytes, content_type)

    # 2. Build a sensible filename for the multipart part
    ext = infer_extension(content_type)
    filename = f"audio.{ext}"

    logger.info("Sending %.1f KB audio to Sarvam STT.", len(audio_bytes) / 1024)

    # 3. Call the API (with retry on transient failures)
    transcript = await _call_sarvam(audio_bytes, filename)

    if not transcript:
        logger.info("Sarvam returned an empty transcript (silence / noise).")
    else:
        logger.info("Sarvam transcript: %r", transcript[:120])

    return transcript
