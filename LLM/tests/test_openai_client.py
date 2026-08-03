from __future__ import annotations

import json
import socket
import urllib.error
from pathlib import Path

import pytest

from LLM.config import OpenAISettings
from LLM.openai_client import (
    OpenAIAuthenticationError,
    OpenAIConnectionError,
    OpenAIPermissionError,
    OpenAIRateLimitError,
    OpenAIResponseError,
    OpenAITimeoutError,
    OpenAIUpstreamHTTPError,
    extract_openai_response,
    generate_openai,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "openai_response_success.json"
SETTINGS = OpenAISettings(
    api_key="dummy-openai-test-key",
    timeout_seconds=300,
    reasoning_effort="medium",
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


def test_extracts_output_text_after_non_message_output_items() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert extract_openai_response(payload) == "확인"


def test_extracts_and_concatenates_all_output_text_parts() -> None:
    payload = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "첫째"},
                    {"type": "refusal", "refusal": "ignored"},
                    {"type": "output_text", "text": "둘째"},
                ],
            }
        ],
    }

    assert extract_openai_response(payload) == "첫째둘째"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "incomplete", "output": []},
        {"status": "completed"},
        {"status": "completed", "output": []},
        {"status": "completed", "output": [{"type": "reasoning"}]},
        {
            "status": "completed",
            "output": [{"type": "message", "content": []}],
        },
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": ""}],
                }
            ],
        },
        [],
    ],
)
def test_rejects_unexpected_incomplete_or_empty_response(payload) -> None:
    with pytest.raises(OpenAIResponseError):
        extract_openai_response(payload)


def test_generate_uses_responses_api_header_auth_and_transient_storage() -> None:
    captured = {}
    clock_values = iter([10.0, 11.25])

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(FIXTURE_PATH.read_bytes())

    result = generate_openai(
        model="gpt-5.6-luna",
        prompt="테스트",
        settings=SETTINGS,
        opener=opener,
        clock=lambda: next(clock_values),
    )

    assert captured == {
        "url": "https://api.openai.com/v1/responses",
        "authorization": "Bearer dummy-openai-test-key",
        "content_type": "application/json; charset=utf-8",
        "payload": {
            "model": "gpt-5.6-luna",
            "input": "테스트",
            "reasoning": {"effort": "medium"},
            "store": False,
        },
        "timeout": 300,
    }
    assert SETTINGS.api_key not in captured["url"]
    assert result.text == "확인"
    assert result.elapsed_ms == 1250


def test_generate_uses_per_model_reasoning_effort_override() -> None:
    captured = {}

    def opener(request, timeout):
        captured["payload"] = json.loads(request.data)
        return FakeResponse(FIXTURE_PATH.read_bytes())

    generate_openai(
        model="gpt-5.6-luna",
        prompt="테스트",
        settings=SETTINGS,
        reasoning_effort="none",
        opener=opener,
    )

    assert captured["payload"]["reasoning"] == {"effort": "none"}


def test_timeout_error_is_safe() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        raise socket.timeout("contains-internal-detail")

    with pytest.raises(OpenAITimeoutError) as exc_info:
        generate_openai(
            model="gpt-5.6-luna",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert "contains-internal-detail" not in str(exc_info.value)
    assert SETTINGS.api_key not in str(exc_info.value)


def test_connection_error_is_safe() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        raise urllib.error.URLError("contains-internal-detail")

    with pytest.raises(OpenAIConnectionError) as exc_info:
        generate_openai(
            model="gpt-5.6-luna",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert "contains-internal-detail" not in str(exc_info.value)
    assert SETTINGS.api_key not in str(exc_info.value)


@pytest.mark.parametrize(
    ("status_code", "exception_type", "message"),
    [
        (401, OpenAIAuthenticationError, "OpenAI API authentication failed."),
        (
            403,
            OpenAIPermissionError,
            "OpenAI API key does not have permission to use the selected model.",
        ),
        (
            429,
            OpenAIRateLimitError,
            "OpenAI API quota or rate limit was exceeded.",
        ),
        (503, OpenAIUpstreamHTTPError, "OpenAI API returned HTTP 503."),
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
        generate_openai(
            model="gpt-5.6-luna",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert str(exc_info.value) == message
    assert SETTINGS.api_key not in str(exc_info.value)


def test_invalid_json_is_rejected() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        return FakeResponse(b"not-json")

    with pytest.raises(OpenAIResponseError, match="invalid JSON"):
        generate_openai(
            model="gpt-5.6-luna",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )
