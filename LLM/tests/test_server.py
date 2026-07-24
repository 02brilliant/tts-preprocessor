from __future__ import annotations

from fastapi import HTTPException
import pytest

from api import server as server_module
from api.server import LLMTransformRequest, app
from LLM.client import GenerationResult, LLMTimeoutError
from LLM.gemini_client import GeminiRateLimitError, GeminiServiceDisabledError


def get_endpoint(path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Missing route: {method} {path}")


@pytest.fixture(autouse=True)
def use_valid_prompt_template(monkeypatch):
    """Keep routing tests independent from the operator-editable prompt file."""

    monkeypatch.setattr(
        server_module,
        "build_prompt",
        lambda text: f"테스트 프롬프트: {text}",
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


def test_transform_rejects_unsupported_model() -> None:
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(LLMTransformRequest(text="원고", model="unknown"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported LLM model."


def test_transform_returns_normalized_public_contract(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured = {}

    def fake_generate(*, model, prompt, settings):
        captured["model"] = model
        captured["prompt_has_text"] = "원고" in prompt
        captured["base_url"] = settings.base_url
        return GenerationResult(text="교정 결과", elapsed_ms=1234.5678)

    monkeypatch.setattr(server_module, "generate", fake_generate)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    result = endpoint(LLMTransformRequest(text="원고", model="gemma4:e4b"))

    assert result == {
        "llm_text": "교정 결과",
        "model": "gemma4:e4b",
        "elapsed_ms": 1234.568,
    }
    assert captured == {
        "model": "gemma4:e4b",
        "prompt_has_text": True,
        "base_url": "http://llm.invalid/api",
    }


def test_gemini_transform_routes_to_gemini_client(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-test-key")
    captured = {}

    def fake_generate_gemini(*, model, prompt, settings):
        captured["model"] = model
        captured["prompt_has_text"] = "원고" in prompt
        captured["api_key_present"] = bool(settings.api_key)
        return GenerationResult(text="제미나이 교정 결과", elapsed_ms=234.5)

    monkeypatch.setattr(server_module, "generate_gemini", fake_generate_gemini)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    result = endpoint(
        LLMTransformRequest(text="원고", model="gemini-3.6-flash")
    )

    assert result == {
        "llm_text": "제미나이 교정 결과",
        "model": "gemini-3.6-flash",
        "elapsed_ms": 234.5,
    }
    assert captured == {
        "model": "gemini-3.6-flash",
        "prompt_has_text": True,
        "api_key_present": True,
    }


def test_missing_gemini_configuration_is_gemini_only_error(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMTransformRequest(text="원고", model="gemini-3.5-flash-lite")
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Required environment variable GEMINI_API_KEY is missing."
    )


def test_missing_runtime_configuration_is_llm_only_error(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(LLMTransformRequest(text="원고", model="gemma4:e4b"))

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
        endpoint(LLMTransformRequest(text="원고", model="gemma4:e4b"))

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
            LLMTransformRequest(text="원고", model="gemini-3.5-flash")
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
            LLMTransformRequest(text="\uc6d0\uace0", model="gemini-3.5-flash")
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == (
        "Gemini API is disabled for this API key's Google Cloud project. "
        "Enable Generative Language API and retry."
    )
