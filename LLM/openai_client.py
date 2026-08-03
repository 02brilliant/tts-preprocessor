from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from LLM.client import GenerationResult
from LLM.config import OpenAISettings


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIClientError(RuntimeError):
    """Base class for safe, user-facing OpenAI upstream failures."""


class OpenAIConnectionError(OpenAIClientError):
    pass


class OpenAITimeoutError(OpenAIClientError):
    pass


class OpenAIAuthenticationError(OpenAIClientError):
    pass


class OpenAIPermissionError(OpenAIClientError):
    pass


class OpenAIRateLimitError(OpenAIClientError):
    pass


class OpenAIUpstreamHTTPError(OpenAIClientError):
    pass


class OpenAIResponseError(OpenAIClientError):
    pass


def extract_openai_response(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise OpenAIResponseError(
            "OpenAI API returned an unexpected response object."
        )

    status = payload.get("status")
    if status is not None and status != "completed":
        raise OpenAIResponseError(
            "OpenAI API response did not complete successfully."
        )

    output = payload.get("output")
    if not isinstance(output, list):
        raise OpenAIResponseError(
            "OpenAI API response is missing the expected output list."
        )

    text_parts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str):
                text_parts.append(text)

    text = "".join(text_parts)
    if not text.strip():
        raise OpenAIResponseError("OpenAI API returned an empty text response.")
    return text


def generate_openai(
    *,
    model: str,
    prompt: str,
    settings: OpenAISettings,
    reasoning_effort: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> GenerationResult:
    effective_reasoning_effort = reasoning_effort or settings.reasoning_effort
    request_body = json.dumps(
        {
            "model": model,
            "input": prompt,
            "reasoning": {"effort": effective_reasoning_effort},
            "store": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=request_body,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    started_at = clock()
    try:
        response = opener(request, timeout=settings.timeout_seconds)
        raw_body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise OpenAIAuthenticationError(
                "OpenAI API authentication failed."
            ) from exc
        if exc.code == 403:
            raise OpenAIPermissionError(
                "OpenAI API key does not have permission to use the selected model."
            ) from exc
        if exc.code == 429:
            raise OpenAIRateLimitError(
                "OpenAI API quota or rate limit was exceeded."
            ) from exc
        raise OpenAIUpstreamHTTPError(
            f"OpenAI API returned HTTP {exc.code}."
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise OpenAITimeoutError("OpenAI API request timed out.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise OpenAITimeoutError("OpenAI API request timed out.") from exc
        raise OpenAIConnectionError("Could not connect to the OpenAI API.") from exc
    except OSError as exc:
        raise OpenAIConnectionError("Could not connect to the OpenAI API.") from exc

    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OpenAIResponseError("OpenAI API returned invalid JSON.") from exc

    text = extract_openai_response(payload)
    elapsed_ms = (clock() - started_at) * 1000
    return GenerationResult(text=text, elapsed_ms=elapsed_ms)
