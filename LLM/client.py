from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from LLM.config import RuntimeSettings


class LLMClientError(RuntimeError):
    """Base class for safe, user-facing upstream failures."""


class LLMConnectionError(LLMClientError):
    pass


class LLMTimeoutError(LLMClientError):
    pass


class LLMUpstreamHTTPError(LLMClientError):
    pass


class LLMResponseError(LLMClientError):
    pass


@dataclass(frozen=True)
class GenerationResult:
    text: str
    elapsed_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def extract_response(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise LLMResponseError("Local LLM server returned an unexpected response object.")

    response = payload.get("response")
    if not isinstance(response, str):
        raise LLMResponseError(
            "Local LLM server response is missing the expected response text."
        )
    if not response:
        raise LLMResponseError("Local LLM server returned an empty response.")
    return response


def generate(
    *,
    model: str,
    prompt: str,
    settings: RuntimeSettings,
    opener: Callable[..., Any] = urllib.request.urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> GenerationResult:
    request_body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.base_url}/generate",
        data=request_body,
        headers={
            "Authorization": f"Bearer {settings.token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    started_at = clock()
    try:
        response = opener(request, timeout=settings.timeout_seconds)
        raw_body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 502:
            raise LLMUpstreamHTTPError(
                "Local LLM server returned HTTP 502. Its proxy backend may be "
                "unavailable; check the local LLM service and retry."
            ) from exc
        raise LLMUpstreamHTTPError(
            f"Local LLM server returned HTTP {exc.code}."
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LLMTimeoutError("Local LLM server request timed out.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise LLMTimeoutError("Local LLM server request timed out.") from exc
        raise LLMConnectionError("Could not connect to the local LLM server.") from exc
    except OSError as exc:
        raise LLMConnectionError("Could not connect to the local LLM server.") from exc

    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LLMResponseError("Local LLM server returned invalid JSON.") from exc

    text = extract_response(payload)
    elapsed_ms = (clock() - started_at) * 1000
    return GenerationResult(text=text, elapsed_ms=elapsed_ms)
