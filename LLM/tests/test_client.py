from __future__ import annotations

import json
import socket
import urllib.error
from pathlib import Path

import pytest

from LLM.client import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUpstreamHTTPError,
    extract_response,
    generate,
)
from LLM.config import RuntimeSettings


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "generate_success.json"
SETTINGS = RuntimeSettings(
    base_url="http://llm.invalid/api",
    token="dummy-test-credential",
    timeout_seconds=300,
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


def test_extracts_observed_response_field() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert extract_response(payload) == "확인"


@pytest.mark.parametrize("payload", [{}, {"response": None}, {"response": ""}, []])
def test_rejects_unexpected_or_empty_response(payload) -> None:
    with pytest.raises(LLMResponseError):
        extract_response(payload)


def test_generate_sends_expected_contract_without_streaming() -> None:
    captured = {}
    clock_values = iter([10.0, 11.25])

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(FIXTURE_PATH.read_bytes())

    result = generate(
        model="gemma4:e4b",
        prompt="테스트",
        settings=SETTINGS,
        opener=opener,
        clock=lambda: next(clock_values),
    )

    assert captured == {
        "url": "http://llm.invalid/api/generate",
        "authorization": "Bearer dummy-test-credential",
        "content_type": "application/json; charset=utf-8",
        "payload": {
            "model": "gemma4:e4b",
            "prompt": "테스트",
            "stream": False,
            "think": False,
        },
        "timeout": 300,
    }
    assert result.text == "확인"
    assert result.elapsed_ms == 1250


def test_timeout_error_is_safe() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        raise socket.timeout("contains-internal-detail")

    with pytest.raises(LLMTimeoutError) as exc_info:
        generate(
            model="gemma4:e4b",
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

    with pytest.raises(LLMConnectionError) as exc_info:
        generate(
            model="gemma4:e4b",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert "contains-internal-detail" not in str(exc_info.value)
    assert SETTINGS.token not in str(exc_info.value)


def test_invalid_json_is_rejected() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        return FakeResponse(b"not-json")

    with pytest.raises(LLMResponseError, match="invalid JSON"):
        generate(
            model="gemma4:e4b",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )


def test_upstream_http_error_exposes_only_status() -> None:
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            503,
            "contains-upstream-detail",
            hdrs=None,
            fp=None,
        )

    with pytest.raises(LLMUpstreamHTTPError) as exc_info:
        generate(
            model="gemma4:e4b",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert str(exc_info.value) == "Local LLM server returned HTTP 503."
    assert SETTINGS.token not in str(exc_info.value)
