from __future__ import annotations

import io


class AudioValidationError(ValueError):
    pass


def validate_audio(audio_bytes: bytes, content_type: str | None = None) -> None:
    if not audio_bytes:
        raise AudioValidationError("Audio payload is empty.")
    if len(audio_bytes) < 500:
        raise AudioValidationError("Audio payload is too small or empty.")
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise AudioValidationError("Audio payload exceeds the 25 MB limit.")


def audio_to_file_like(audio_bytes: bytes, filename: str) -> io.BytesIO:
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename
    return file_obj


def infer_extension(content_type: str | None) -> str:
    content_type = (content_type or "audio/webm").lower()
    if "ogg" in content_type:
        return "ogg"
    if "wav" in content_type:
        return "wav"
    if "mp3" in content_type or "mpeg" in content_type:
        return "mp3"
    if "mp4" in content_type:
        return "mp4"
    return "webm"
