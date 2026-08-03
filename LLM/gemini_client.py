from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from LLM.client import GenerationResult
from LLM.config import GeminiSettings


GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiClientError(RuntimeError):
    """Base class for safe, user-facing Gemini upstream failures."""


class GeminiConnectionError(GeminiClientError):
    pass


class GeminiTimeoutError(GeminiClientError):
    pass


class GeminiAuthenticationError(GeminiClientError):
    pass


class GeminiServiceDisabledError(GeminiClientError):
    pass


class GeminiAPIKeyRestrictionError(GeminiClientError):
    pass


class GeminiRateLimitError(GeminiClientError):
    pass


class GeminiUpstreamHTTPError(GeminiClientError):
    pass


class GeminiResponseError(GeminiClientError):
    pass


def extract_gemini_response(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise GeminiResponseError(
            "Gemini API returned an unexpected response object."
        )

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GeminiResponseError(
            "Gemini API response is missing the expected candidate."
        )
    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise GeminiResponseError(
            "Gemini API response contains an invalid candidate."
        )
    content = first_candidate.get("content")
    if not isinstance(content, dict):
        raise GeminiResponseError(
            "Gemini API response is missing candidate content."
        )
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], dict):
        raise GeminiResponseError(
            "Gemini API response is missing candidate text."
        )
    text = parts[0].get("text")
    if not isinstance(text, str):
        raise GeminiResponseError(
            "Gemini API response is missing candidate text."
        )
    if not text.strip():
        raise GeminiResponseError("Gemini API returned an empty response.")
    return text


def generate_gemini(
    *,
    model: str,
    prompt: str,
    settings: GeminiSettings,
    opener: Callable[..., Any] = urllib.request.urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> GenerationResult:
    request_body = json.dumps(
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        },
        ensure_ascii=False,
    ).encode("utf-8")
    encoded_model = urllib.parse.quote(model, safe="")
    request = urllib.request.Request(
        f"{GEMINI_API_BASE_URL}/models/{encoded_model}:generateContent",
        data=request_body,
        headers={
            "x-goog-api-key": settings.api_key,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    started_at = clock()
    try:
        response = opener(request, timeout=settings.timeout_seconds)
        raw_body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            error_message = _extract_gemini_error_message(exc)
            if exc.code == 403 and _is_generative_language_api_disabled(error_message):
                raise GeminiServiceDisabledError(
                    "Gemini API is disabled for this API key's Google Cloud "
                    "project. Enable Generative Language API and retry."
                ) from exc
            if exc.code == 403 and _is_gemini_api_key_restricted(error_message):
                raise GeminiAPIKeyRestrictionError(
                    "Gemini API key is blocked from calling Generative Language "
                    "API. Restrict or replace the key for Gemini API and retry."
                ) from exc
            raise GeminiAuthenticationError(
                "Gemini API authentication or permission failed."
            ) from exc
        if exc.code == 429:
            raise GeminiRateLimitError(
                "Gemini API quota or rate limit was exceeded."
            ) from exc
        raise GeminiUpstreamHTTPError(
            f"Gemini API returned HTTP {exc.code}."
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise GeminiTimeoutError("Gemini API request timed out.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise GeminiTimeoutError("Gemini API request timed out.") from exc
        raise GeminiConnectionError("Could not connect to the Gemini API.") from exc
    except OSError as exc:
        raise GeminiConnectionError("Could not connect to the Gemini API.") from exc

    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeminiResponseError("Gemini API returned invalid JSON.") from exc

    text = extract_gemini_response(payload)
    elapsed_ms = (clock() - started_at) * 1000
    return GenerationResult(text=text, elapsed_ms=elapsed_ms)


def _extract_gemini_error_message(error: urllib.error.HTTPError) -> str | None:
    """Read only the structured upstream message needed for classification."""
    try:
        raw_body = error.read()
        payload = json.loads(raw_body)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    upstream_error = payload.get("error")
    if not isinstance(upstream_error, dict):
        return None
    message = upstream_error.get("message")
    if not isinstance(message, str):
        return None
    return message


def _is_generative_language_api_disabled(error_message: str | None) -> bool:
    """Recognize the documented API-disabled response without exposing it."""
    if error_message is None:
        return False
    normalized = error_message.lower()
    return (
        "generativelanguage.googleapis.com" in normalized
        and ("disabled" in normalized or "has not been used" in normalized)
    )


def _is_gemini_api_key_restricted(error_message: str | None) -> bool:
    """Recognize Gemini API-key API restrictions without exposing upstream text."""
    if error_message is None:
        return False
    normalized = error_message.lower()
    return (
        "generativelanguage.googleapis.com" in normalized
        and ("are blocked" in normalized or "api_key_service_blocked" in normalized)
    )
