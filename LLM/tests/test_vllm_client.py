from __future__ import annotations

import json
import socket
import urllib.error
from pathlib import Path

import pytest

from LLM.config import VllmSettings
from LLM.vllm_client import (
    VllmAuthenticationError,
    VllmConnectionError,
    VllmPermissionError,
    VllmRateLimitError,
    VllmResponseError,
    VllmTimeoutError,
    VllmUpstreamHTTPError,
    chat_completions_url,
    extract_vllm_response,
    generate_vllm,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vllm_chat_success.json"
SETTINGS = VllmSettings(
    base_url="http://vllm.invalid",
    token="dummy-vllm-test-token",
    timeout_seconds=300,
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://vllm.invalid", "http://vllm.invalid/v1/chat/completions"),
        ("http://vllm.invalid/", "http://vllm.invalid/v1/chat/completions"),
        ("http://vllm.invalid/v1", "http://vllm.invalid/v1/chat/completions"),
        ("http://vllm.invalid/v1/", "http://vllm.invalid/v1/chat/completions"),
        (
            "http://vllm.invalid/v1/chat/completions",
            "http://vllm.invalid/v1/chat/completions",
        ),
        (
            "http://gateway.invalid/openai/v1",
            "http://gateway.invalid/openai/v1/chat/completions",
        ),
        (
            "http://gateway.invalid/api/v1/apps/example-app-id",
            "http://gateway.invalid/api/v1/apps/example-app-id/v1/chat/completions",
        ),
    ],
)
def test_chat_completions_url_normalizes_base_url(base_url: str, expected: str) -> None:
    assert chat_completions_url(base_url) == expected


def test_extracts_chat_completion_message_content() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert extract_vllm_response(payload) == "확인"


def test_extracts_completions_style_text_fallback() -> None:
    payload = {"choices": [{"text": "확인"}]}

    assert extract_vllm_response(payload) == "확인"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "   "}}]},
        {"choices": [{"text": ""}]},
        {"choices": [None]},
        [],
    ],
)
def test_rejects_unexpected_or_empty_response(payload) -> None:
    with pytest.raises(VllmResponseError):
        extract_vllm_response(payload)


def test_generate_uses_chat_completions_and_bearer_auth() -> None:
    captured = {}
    clock_values = iter([10.0, 11.25])

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(FIXTURE_PATH.read_bytes())

    result = generate_vllm(
        model="google/gemma-4-31B-it",
        prompt="테스트",
        settings=SETTINGS,
        opener=opener,
        clock=lambda: next(clock_values),
    )

    assert captured == {
        "url": "http://vllm.invalid/v1/chat/completions",
        "authorization": "Bearer dummy-vllm-test-token",
        "content_type": "application/json; charset=utf-8",
        "payload": {
            "model": "google/gemma-4-31B-it",
            "messages": [{"role": "user", "content": "테스트"}],
            "stream": False,
        },
        "timeout": 300,
    }
    assert SETTINGS.token not in captured["url"]
    assert result.text == "확인"
    assert result.elapsed_ms == 1250


def test_timeout_error_is_safe() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        raise socket.timeout("contains-internal-detail")

    with pytest.raises(VllmTimeoutError) as exc_info:
        generate_vllm(
            model="google/gemma-4-31B-it",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert "contains-internal-detail" not in str(exc_info.value)
    assert SETTINGS.token not in str(exc_info.value)


def test_connection_error_is_safe() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        raise urllib.error.URLError("contains-internal-detail")

    with pytest.raises(VllmConnectionError) as exc_info:
        generate_vllm(
            model="google/gemma-4-31B-it",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert "contains-internal-detail" not in str(exc_info.value)
    assert SETTINGS.token not in str(exc_info.value)


@pytest.mark.parametrize(
    ("status_code", "exception_type", "message"),
    [
        (401, VllmAuthenticationError, "vLLM server authentication failed."),
        (
            403,
            VllmPermissionError,
            "vLLM token does not have permission to use the selected model.",
        ),
        (
            429,
            VllmRateLimitError,
            "vLLM server quota or rate limit was exceeded.",
        ),
        (503, VllmUpstreamHTTPError, "vLLM server returned HTTP 503."),
    ],
)
def test_http_errors_are_safely_classified(
    status_code,
    exception_type,
    message,
) -> None:
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            status_code,
            "contains-upstream-detail",
            hdrs=None,
            fp=None,
        )

    with pytest.raises(exception_type) as exc_info:
        generate_vllm(
            model="google/gemma-4-31B-it",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert str(exc_info.value) == message
    assert SETTINGS.token not in str(exc_info.value)


def test_invalid_json_is_rejected() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        return FakeResponse(b"not-json")

    with pytest.raises(VllmResponseError, match="invalid JSON"):
        generate_vllm(
            model="google/gemma-4-31B-it",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )
