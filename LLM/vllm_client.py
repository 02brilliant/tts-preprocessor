from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from LLM.client import GenerationResult
from LLM.config import VllmSettings


class VllmClientError(RuntimeError):
    """Base class for safe, user-facing vLLM upstream failures."""


class VllmConnectionError(VllmClientError):
    pass


class VllmTimeoutError(VllmClientError):
    pass


class VllmAuthenticationError(VllmClientError):
    pass


class VllmPermissionError(VllmClientError):
    pass


class VllmRateLimitError(VllmClientError):
    pass


class VllmUpstreamHTTPError(VllmClientError):
    pass


class VllmResponseError(VllmClientError):
    pass


def chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def extract_vllm_response(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise VllmResponseError(
            "vLLM server returned an unexpected response object."
        )

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise VllmResponseError(
            "vLLM server response is missing the expected choices."
        )

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise VllmResponseError(
            "vLLM server response contains an invalid choice."
        )

    message = first_choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

    text = first_choice.get("text")
    if isinstance(text, str) and text.strip():
        return text

    raise VllmResponseError("vLLM server returned an empty text response.")


def extract_vllm_usage(payload: Any) -> tuple[int | None, int | None]:
    if not isinstance(payload, dict):
        return None, None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None, None
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    return (
        prompt_tokens if isinstance(prompt_tokens, int) and prompt_tokens >= 0 else None,
        completion_tokens
        if isinstance(completion_tokens, int) and completion_tokens >= 0
        else None,
    )


def generate_vllm(
    *,
    model: str,
    prompt: str,
    settings: VllmSettings,
    opener: Callable[..., Any] = urllib.request.urlopen,
    clock: Callable[[], float] = time.perf_counter,
) -> GenerationResult:
    request_body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        chat_completions_url(settings.base_url),
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
        if exc.code == 401:
            raise VllmAuthenticationError(
                "vLLM server authentication failed."
            ) from exc
        if exc.code == 403:
            raise VllmPermissionError(
                "vLLM token does not have permission to use the selected model."
            ) from exc
        if exc.code == 429:
            raise VllmRateLimitError(
                "vLLM server quota or rate limit was exceeded."
            ) from exc
        raise VllmUpstreamHTTPError(
            f"vLLM server returned HTTP {exc.code}."
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise VllmTimeoutError("vLLM server request timed out.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise VllmTimeoutError("vLLM server request timed out.") from exc
        raise VllmConnectionError("Could not connect to the vLLM server.") from exc
    except OSError as exc:
        raise VllmConnectionError("Could not connect to the vLLM server.") from exc

    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VllmResponseError("vLLM server returned invalid JSON.") from exc

    text = extract_vllm_response(payload)
    prompt_tokens, completion_tokens = extract_vllm_usage(payload)
    elapsed_ms = (clock() - started_at) * 1000
    return GenerationResult(
        text=text,
        elapsed_ms=elapsed_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
