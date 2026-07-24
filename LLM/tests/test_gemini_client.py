from __future__ import annotations

import json
import socket
import urllib.error
from io import BytesIO
from pathlib import Path

import pytest

from LLM.config import GeminiSettings
from LLM.gemini_client import (
    GeminiAuthenticationError,
    GeminiConnectionError,
    GeminiRateLimitError,
    GeminiResponseError,
    GeminiServiceDisabledError,
    GeminiTimeoutError,
    GeminiUpstreamHTTPError,
    extract_gemini_response,
    generate_gemini,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gemini_generate_success.json"
SETTINGS = GeminiSettings(
    api_key="dummy-gemini-test-key",
    timeout_seconds=300,
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


def test_extracts_documented_generate_content_text_field() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert extract_gemini_response(payload) == "확인"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"candidates": []},
        {"candidates": [{}]},
        {"candidates": [{"content": {}}]},
        {"candidates": [{"content": {"parts": []}}]},
        {"candidates": [{"content": {"parts": [{}]}}]},
        {"candidates": [{"content": {"parts": [{"text": ""}]}}]},
        [],
    ],
)
def test_rejects_unexpected_or_empty_response(payload) -> None:
    with pytest.raises(GeminiResponseError):
        extract_gemini_response(payload)


def test_generate_sends_prompt_only_contract_with_header_authentication() -> None:
    captured = {}
    clock_values = iter([10.0, 11.25])

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["api_key"] = request.get_header("X-goog-api-key")
        captured["content_type"] = request.get_header("Content-type")
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(FIXTURE_PATH.read_bytes())

    result = generate_gemini(
        model="gemini-3.6-flash",
        prompt="테스트",
        settings=SETTINGS,
        opener=opener,
        clock=lambda: next(clock_values),
    )

    assert captured == {
        "url": (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-3.6-flash:generateContent"
        ),
        "api_key": "dummy-gemini-test-key",
        "content_type": "application/json; charset=utf-8",
        "payload": {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "테스트"}],
                }
            ]
        },
        "timeout": 300,
    }
    assert SETTINGS.api_key not in captured["url"]
    assert result.text == "확인"
    assert result.elapsed_ms == 1250


def test_timeout_error_is_safe() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        raise socket.timeout("contains-internal-detail")

    with pytest.raises(GeminiTimeoutError) as exc_info:
        generate_gemini(
            model="gemini-3.6-flash",
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

    with pytest.raises(GeminiConnectionError) as exc_info:
        generate_gemini(
            model="gemini-3.6-flash",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert "contains-internal-detail" not in str(exc_info.value)
    assert SETTINGS.api_key not in str(exc_info.value)


@pytest.mark.parametrize(
    ("status_code", "exception_type", "message"),
    [
        (
            401,
            GeminiAuthenticationError,
            "Gemini API authentication or permission failed.",
        ),
        (
            403,
            GeminiAuthenticationError,
            "Gemini API authentication or permission failed.",
        ),
        (
            429,
            GeminiRateLimitError,
            "Gemini API quota or rate limit was exceeded.",
        ),
        (503, GeminiUpstreamHTTPError, "Gemini API returned HTTP 503."),
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
        generate_gemini(
            model="gemini-3.6-flash",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )

    assert str(exc_info.value) == message
    assert SETTINGS.api_key not in str(exc_info.value)


def test_api_disabled_403_has_safe_remediation_message() -> None:
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            403,
            "contains-upstream-detail",
            hdrs=None,
            fp=BytesIO(
                b'{"error":{"code":403,"status":"PERMISSION_DENIED",'
                b'"message":"Gemini API has not been used in project 123 or '
                b'it is disabled. Enable it at generativelanguage.googleapis.com"}}'
            ),
        )

    with pytest.raises(GeminiServiceDisabledError) as exc_info:
        generate_gemini(
            model="gemini-3.6-flash",
            prompt="\ud14c\uc2a4\ud2b8",
            settings=SETTINGS,
            opener=opener,
        )

    assert str(exc_info.value) == (
        "Gemini API is disabled for this API key's Google Cloud project. "
        "Enable Generative Language API and retry."
    )
    assert SETTINGS.api_key not in str(exc_info.value)


def test_invalid_json_is_rejected() -> None:
    def opener(_request, timeout):
        assert timeout == 300
        return FakeResponse(b"not-json")

    with pytest.raises(GeminiResponseError, match="invalid JSON"):
        generate_gemini(
            model="gemini-3.6-flash",
            prompt="테스트",
            settings=SETTINGS,
            opener=opener,
        )
