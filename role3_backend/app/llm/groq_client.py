"""
Groq LLM client with Tenacity retry logic.

Uses Groq's JSON mode to enforce structured output.
The response is parsed into LLMAnswer (Pydantic) before being returned.

Retry policy:
  - Retries only on transient failures (network errors, 429, 503).
  - Does NOT retry on: invalid queries, auth errors, malformed output.
  - Bounded: max_retries from settings (default 3).
  - Exponential backoff with jitter.
"""

from __future__ import annotations

import json
import logging

from groq import AsyncGroq, RateLimitError, APIConnectionError, InternalServerError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)
from pydantic import ValidationError

from app.config import settings
from app.schemas import LLMAnswer

logger = logging.getLogger(__name__)

# Exceptions that are worth retrying (transient)
_RETRYABLE = (RateLimitError, APIConnectionError, InternalServerError)


class LLMGenerationError(Exception):
    """Raised when Groq fails after all retries or returns malformed output."""


class GroqClient:
    """Async Groq client. One instance shared across requests."""

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)

    async def generate(self, system_prompt: str, user_message: str) -> LLMAnswer:
        """
        Call Groq with JSON mode and parse the response into LLMAnswer.
        Retries on transient failures only.
        """
        raw = await self._call_with_retry(system_prompt, user_message)
        return self._parse(raw)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential_jitter(initial=0.1, max=2.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call_with_retry(self, system_prompt: str, user_message: str) -> str:
        """Raw Groq call wrapped by Tenacity. Tries primary model then fallback models."""
        models_to_try = [settings.groq_model, "llama-3.1-8b-instant", "llama3-8b-8192"]
        # Deduplicate while preserving order
        seen = set()
        models = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

        last_error = None
        for model in models:
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.0,   # deterministic output for grounding consistency
                    max_tokens=512,    # keep generation short — latency-sensitive path
                )
                content = response.choices[0].message.content
                if content:
                    return content
            except Exception as e:
                logger.warning("Groq call failed for model '%s': %s. Trying fallback model...", model, e)
                last_error = e

        raise LLMGenerationError(f"Groq generation failed across models: {last_error}")

    @staticmethod
    def _parse(raw: str) -> LLMAnswer:
        """Parse and validate the raw JSON string into LLMAnswer."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMGenerationError(f"Groq returned non-JSON output: {raw!r}") from exc

        try:
            return LLMAnswer.model_validate(data)
        except ValidationError as exc:
            raise LLMGenerationError(
                f"Groq output did not match LLMAnswer schema: {exc}"
            ) from exc
