"""
tests/test_stt.py — Unit tests for the Role 2 STT module (Role 2)

Tests are written so they run WITHOUT network access.
All Sarvam HTTP calls are mocked with unittest.mock.

Run:
    pytest tests/test_stt.py -v
"""

from __future__ import annotations

import io
import sys
import os
import pytest

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root without installing the package
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Tests: audio.py
# ---------------------------------------------------------------------------

from app.stt.audio import (
    AudioValidationError,
    audio_to_file_like,
    infer_extension,
    validate_audio,
    MIN_AUDIO_BYTES,
    MAX_AUDIO_BYTES,
)


class TestValidateAudio:

    def test_raises_on_empty_bytes(self):
        with pytest.raises(AudioValidationError, match="empty"):
            validate_audio(b"")

    def test_raises_on_none_like_empty(self):
        with pytest.raises(AudioValidationError):
            validate_audio(b"")

    def test_raises_below_min_size(self):
        tiny = b"x" * (MIN_AUDIO_BYTES - 1)
        with pytest.raises(AudioValidationError, match="too small"):
            validate_audio(tiny)

    def test_raises_above_max_size(self):
        huge = b"x" * (MAX_AUDIO_BYTES + 1)
        with pytest.raises(AudioValidationError, match="too large"):
            validate_audio(huge)

    def test_passes_for_valid_size(self):
        valid = b"x" * MIN_AUDIO_BYTES
        # Should not raise
        validate_audio(valid)

    def test_known_mime_types_do_not_raise(self):
        valid = b"x" * MIN_AUDIO_BYTES
        for mime in ("audio/webm", "audio/ogg", "audio/wav", "audio/mp4"):
            validate_audio(valid, content_type=mime)

    def test_unknown_mime_type_logs_warning_but_does_not_raise(self, caplog):
        import logging
        valid = b"x" * MIN_AUDIO_BYTES
        with caplog.at_level(logging.WARNING, logger="app.stt.audio"):
            validate_audio(valid, content_type="audio/flac")
        assert "unrecognised" in caplog.text.lower()

    def test_none_content_type_accepted(self):
        valid = b"x" * MIN_AUDIO_BYTES
        validate_audio(valid, content_type=None)


class TestAudioToFileLike:

    def test_returns_bytesio(self):
        buf = audio_to_file_like(b"hello", "test.webm")
        assert isinstance(buf, io.BytesIO)

    def test_name_attribute_set(self):
        buf = audio_to_file_like(b"hello", "my_audio.ogg")
        assert buf.name == "my_audio.ogg"

    def test_content_readable(self):
        data = b"audio data"
        buf = audio_to_file_like(data)
        assert buf.read() == data


class TestInferExtension:

    def test_webm(self):
        assert infer_extension("audio/webm") == "webm"

    def test_webm_with_codecs(self):
        assert infer_extension("audio/webm;codecs=opus") == "webm"

    def test_ogg(self):
        assert infer_extension("audio/ogg;codecs=opus") == "ogg"

    def test_wav(self):
        assert infer_extension("audio/x-wav") == "wav"

    def test_mp3(self):
        assert infer_extension("audio/mpeg") == "mp3"

    def test_mp4(self):
        assert infer_extension("audio/mp4") == "mp4"

    def test_none_returns_webm(self):
        assert infer_extension(None) == "webm"

    def test_unknown_returns_webm(self):
        assert infer_extension("audio/unknown-format") == "webm"


# ---------------------------------------------------------------------------
# Tests: sarvam_client.py (mocked HTTP)
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestTranscribe:
    """Tests for the public transcribe() function with all HTTP mocked."""

    VALID_AUDIO = b"x" * MIN_AUDIO_BYTES

    @pytest.mark.asyncio
    async def test_returns_transcript_on_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transcript": "What is machine learning?"}

        with patch("app.stt.sarvam_client._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from app.stt.sarvam_client import transcribe
            result = await transcribe(self.VALID_AUDIO, "audio/webm")

        assert result == "What is machine learning?"

    @pytest.mark.asyncio
    async def test_raises_audio_validation_error_on_empty_bytes(self):
        from app.stt.sarvam_client import transcribe
        with pytest.raises(AudioValidationError):
            await transcribe(b"", "audio/webm")

    @pytest.mark.asyncio
    async def test_raises_sarvam_stt_error_on_401(self):
        from app.stt.sarvam_client import SarvamSTTError, transcribe

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("app.stt.sarvam_client._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            with pytest.raises(SarvamSTTError, match="401"):
                await transcribe(self.VALID_AUDIO)

    @pytest.mark.asyncio
    async def test_raises_sarvam_stt_error_on_400(self):
        from app.stt.sarvam_client import SarvamSTTError, transcribe

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("app.stt.sarvam_client._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            with pytest.raises(SarvamSTTError):
                await transcribe(self.VALID_AUDIO)

    @pytest.mark.asyncio
    async def test_empty_transcript_returned_as_empty_string(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transcript": ""}

        with patch("app.stt.sarvam_client._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from app.stt.sarvam_client import transcribe
            result = await transcribe(self.VALID_AUDIO)

        assert result == ""

    @pytest.mark.asyncio
    async def test_transcript_is_stripped(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"transcript": "  hello world  "}

        with patch("app.stt.sarvam_client._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            from app.stt.sarvam_client import transcribe
            result = await transcribe(self.VALID_AUDIO)

        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_raises_on_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("SARVAM_API_KEY", raising=False)
        # Reset the cached client so it re-reads the env
        import app.stt.sarvam_client as sc
        sc._client = None

        from app.stt.sarvam_client import transcribe
        with pytest.raises(EnvironmentError, match="SARVAM_API_KEY"):
            await transcribe(self.VALID_AUDIO)


# ---------------------------------------------------------------------------
# Tests: benchmark percentile calculator
# ---------------------------------------------------------------------------

class TestPercentile:
    """Test the pure percentile function in benchmark_latency.py."""

    def test_p50_single_value(self):
        from benchmarks.benchmark_latency import p50
        assert p50([42.0]) == pytest.approx(42.0)

    def test_p50_two_values(self):
        from benchmarks.benchmark_latency import p50
        assert p50([10.0, 20.0]) == pytest.approx(15.0)

    def test_p100_is_max(self):
        from benchmarks.benchmark_latency import p100
        data = [5.0, 10.0, 15.0, 200.0]
        assert p100(data) == pytest.approx(200.0)

    def test_p70(self):
        from benchmarks.benchmark_latency import p70
        # 10 values: 1..10
        data = [float(i) for i in range(1, 11)]
        # P70 at index 6.3 → 6 + 0.3*(7-6) = 6.3
        assert p70(data) == pytest.approx(7.3)

    def test_raises_on_empty(self):
        from benchmarks.benchmark_latency import percentile
        with pytest.raises(ValueError):
            percentile([], 0.50)
