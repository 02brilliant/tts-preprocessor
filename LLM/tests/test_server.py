from __future__ import annotations

from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
import pytest

from api import server as server_module
from api.server import (
    LLMProsodyRequest,
    LLMSpeechRequest,
    LLMTransformRequest,
    app,
)
from LLM.client import GenerationResult, LLMTimeoutError
from LLM.gemini_client import GeminiRateLimitError, GeminiServiceDisabledError


def get_endpoint(path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(
            route,
            "methods",
            set(),
        ):
            return route.endpoint
    raise AssertionError(f"Missing route: {method} {path}")


@pytest.fixture(autouse=True)
def use_valid_stage_prompt_templates(monkeypatch):
    """Keep routing tests independent from operator-editable prompt files."""

    monkeypatch.setattr(
        server_module,
        "build_prosody_prompt",
        lambda text: f"PROSODY INPUT: {text}",
    )
    monkeypatch.setattr(
        server_module,
        "build_speech_prompt",
        lambda text: f"SPEECH INPUT: {text}",
    )


def test_existing_and_llm_api_routes_are_registered() -> None:
    assert get_endpoint("/api/transform", "POST")
    assert get_endpoint("/api/llm/models", "GET")() == {
        "models": [
            "gemma4:31b",
            "gemma4:26b",
            "gemma4:e4b",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
        ],
        "default_model": "gemma4:e4b",
    }
    assert get_endpoint("/api/llm/transform", "POST")


@pytest.mark.parametrize(
    "payload",
    (
        {"normalized_text": "원고", "model": "gemma4:e4b"},
        {"stage": "prosody", "prosody_text": "원고", "model": "gemma4:e4b"},
        {
            "stage": "speech",
            "prosody_text": "원고",
            "normalized_text": "잘못된 필드",
            "model": "gemma4:e4b",
        },
    ),
)
def test_transform_request_requires_stage_specific_fields(payload: dict) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(LLMTransformRequest).validate_python(payload)


def test_transform_rejects_unsupported_model() -> None:
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMProsodyRequest(
                stage="prosody",
                normalized_text="원고",
                model="unknown",
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported LLM model."


def test_local_prosody_returns_stage_specific_contract(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured = {}

    def fake_generate(*, model, prompt, settings):
        captured["model"] = model
        captured["prompt"] = prompt
        captured["base_url"] = settings.base_url
        return GenerationResult(text="원고, ", elapsed_ms=1234.5678)

    monkeypatch.setattr(server_module, "generate", fake_generate)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    result = endpoint(
        LLMProsodyRequest(
            stage="prosody",
            normalized_text="원고",
            model="gemma4:e4b",
        )
    )

    assert result == {
        "prosody_text": "원고, ",
        "model": "gemma4:e4b",
        "elapsed_ms": 1234.568,
    }
    assert captured == {
        "model": "gemma4:e4b",
        "prompt": "PROSODY INPUT: 원고",
        "base_url": "http://llm.invalid/api",
    }


def test_gemini_speech_routes_to_gemini_client(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-test-key")
    captured = {}

    def fake_generate_gemini(*, model, prompt, settings):
        captured["model"] = model
        captured["prompt"] = prompt
        captured["api_key_present"] = bool(settings.api_key)
        return GenerationResult(text="궁무른, 조씀니다.", elapsed_ms=234.5)

    monkeypatch.setattr(server_module, "generate_gemini", fake_generate_gemini)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    result = endpoint(
        LLMSpeechRequest(
            stage="speech",
            prosody_text="국물은, 좋습니다.",
            model="gemini-3.6-flash",
        )
    )

    assert result == {
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemini-3.6-flash",
        "elapsed_ms": 234.5,
    }
    assert captured == {
        "model": "gemini-3.6-flash",
        "prompt": "SPEECH INPUT: 국물은, 좋습니다.",
        "api_key_present": True,
    }


def test_two_stages_use_same_model_and_exact_previous_result(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    responses = iter(("원고, 다음", "원고, 다음"))
    captured: list[tuple[str, str]] = []

    def fake_generate(*, model, prompt, settings):
        captured.append((model, prompt))
        return GenerationResult(text=next(responses), elapsed_ms=1.0)

    monkeypatch.setattr(server_module, "generate", fake_generate)
    endpoint = get_endpoint("/api/llm/transform", "POST")
    prosody = endpoint(
        LLMProsodyRequest(
            stage="prosody",
            normalized_text="원고 다음",
            model="gemma4:e4b",
        )
    )["prosody_text"]
    speech = endpoint(
        LLMSpeechRequest(
            stage="speech",
            prosody_text=prosody,
            model="gemma4:e4b",
        )
    )["speech_text"]

    assert speech == "원고, 다음"
    assert captured == [
        ("gemma4:e4b", "PROSODY INPUT: 원고 다음"),
        ("gemma4:e4b", "SPEECH INPUT: 원고, 다음"),
    ]


def test_invalid_prosody_response_maps_to_bad_gateway(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    monkeypatch.setattr(
        server_module,
        "generate",
        lambda **_kwargs: GenerationResult(text="다른 원고", elapsed_ms=1.0),
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMProsodyRequest(
                stage="prosody",
                normalized_text="원고",
                model="gemma4:e4b",
            )
        )

    assert exc_info.value.status_code == 502
    assert "changed existing text" in exc_info.value.detail


def test_missing_gemini_configuration_is_gemini_only_error(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMSpeechRequest(
                stage="speech",
                prosody_text="원고",
                model="gemini-3.5-flash-lite",
            )
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Required environment variable GEMINI_API_KEY is missing."
    )


def test_missing_runtime_configuration_is_local_only_error(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMProsodyRequest(
                stage="prosody",
                normalized_text="원고",
                model="gemma4:e4b",
            )
        )

    assert exc_info.value.status_code == 503
    assert "LOCAL_LLM_BASE_URL" in exc_info.value.detail


def test_upstream_timeout_maps_to_gateway_timeout(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")

    def fake_generate(**_kwargs):
        raise LLMTimeoutError("Local LLM server request timed out.")

    monkeypatch.setattr(server_module, "generate", fake_generate)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMProsodyRequest(
                stage="prosody",
                normalized_text="원고",
                model="gemma4:e4b",
            )
        )

    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "Local LLM server request timed out."


def test_gemini_rate_limit_maps_to_too_many_requests(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-test-key")

    def fake_generate_gemini(**_kwargs):
        raise GeminiRateLimitError(
            "Gemini API quota or rate limit was exceeded."
        )

    monkeypatch.setattr(server_module, "generate_gemini", fake_generate_gemini)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMSpeechRequest(
                stage="speech",
                prosody_text="원고",
                model="gemini-3.5-flash",
            )
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == (
        "Gemini API quota or rate limit was exceeded."
    )


def test_gemini_service_disabled_maps_to_service_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-test-key")

    def fake_generate_gemini(**_kwargs):
        raise GeminiServiceDisabledError(
            "Gemini API is disabled for this API key's Google Cloud project. "
            "Enable Generative Language API and retry."
        )

    monkeypatch.setattr(server_module, "generate_gemini", fake_generate_gemini)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMSpeechRequest(
                stage="speech",
                prosody_text="원고",
                model="gemini-3.5-flash",
            )
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Gemini API is disabled for this API key's Google Cloud project. "
        "Enable Generative Language API and retry."
    )
