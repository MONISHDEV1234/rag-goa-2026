from __future__ import annotations

import os

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .audio import audio_to_file_like, infer_extension, validate_audio

SARVAM_API_URL = "https://api.sarvam.ai/speech-to-text"


class SarvamSTTError(RuntimeError):
    pass


class SarvamTransientError(IOError):
    pass


from app.config import settings


def _api_key() -> str:
    key = (getattr(settings, "sarvam_api_key", None) or os.environ.get("SARVAM_API_KEY", "")).strip()
    if not key:
        raise SarvamSTTError("SARVAM_API_KEY is not configured.")
    return key


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 200:
        return
    message = response.text[:500]
    if response.status_code == 429 or response.status_code >= 500:
        raise SarvamTransientError(f"Sarvam returned {response.status_code}: {message}")
    raise SarvamSTTError(f"Sarvam returned {response.status_code}: {message}")


@retry(
    retry=retry_if_exception_type(SarvamTransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def _request(audio_bytes: bytes, filename: str, content_type: str | None = None) -> str:
    headers = {"api-subscription-key": _api_key()}
    mime = (content_type or "audio/webm").split(";")[0].strip()
    model = os.environ.get("SARVAM_STT_MODEL", "saarika:v2.5")
    lang = os.environ.get("SARVAM_LANGUAGE_CODE", "unknown")

    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            response = await client.post(
                SARVAM_API_URL,
                headers=headers,
                files={"file": (filename, audio_to_file_like(audio_bytes, filename), mime)},
                data={
                    "model": model,
                    "language_code": lang,
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise SarvamTransientError(str(exc)) from exc
    _raise_for_status(response)
    payload = response.json()
    transcript = payload.get("transcript", "") if isinstance(payload, dict) else ""
    detected_lang = payload.get("language_code", "unknown") if isinstance(payload, dict) else "unknown"
    print(f"[Sarvam STT] Audio {len(audio_bytes)}B ({mime}) -> Lang: {detected_lang} -> Transcript: '{transcript}'")
    if not isinstance(transcript, str):
        raise SarvamSTTError("Sarvam returned an invalid transcript.")
    return transcript.strip()


async def transcribe(audio_bytes: bytes, content_type: str | None = None) -> str:
    validate_audio(audio_bytes, content_type)
    ext = infer_extension(content_type)
    return await _request(audio_bytes, f"audio.{ext}", content_type)
