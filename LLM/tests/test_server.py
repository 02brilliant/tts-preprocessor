from __future__ import annotations

from fastapi import HTTPException
from pydantic import ValidationError
import pytest

from api import server as server_module
from api.binary_runtime import BinaryRuntimeError, LLMStageRuntimeError
from api.server import LLMTransformRequest, app


def get_endpoint(path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(
            route,
            "methods",
            set(),
        ):
            return route.endpoint
    raise AssertionError(f"Missing route: {method} {path}")


def test_existing_and_llm_api_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "list_llm_stage_models",
        lambda: {
            "models": [
                "gemma4:31b",
                "gemma4:26b",
                "gemma4:e4b",
                "gemma4-31B-it (vLLM)",
                "gemini-3.6-flash",
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gpt-5.6-luna (medium)",
                "gpt-5.6-luna (low)",
                "gpt-5.6-luna (none)",
            ],
            "default_model": "gemma4:31b",
        },
    )
    assert get_endpoint("/api/transform", "POST")
    assert get_endpoint("/api/llm/models", "GET")() == {
        "models": [
            "gemma4:31b",
            "gemma4:26b",
            "gemma4:e4b",
            "gemma4-31B-it (vLLM)",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gpt-5.6-luna (medium)",
            "gpt-5.6-luna (low)",
            "gpt-5.6-luna (none)",
        ],
        "default_model": "gemma4:31b",
    }
    assert get_endpoint("/api/llm/transform", "POST")


@pytest.mark.parametrize(
    "payload",
    (
        {"model": "gemma4:31b"},
        {
            "stage": "prosody",
            "normalized_text": "원고",
            "model": "gemma4:31b",
        },
        {
            "normalized_text": "원고",
            "prosody_text": "이전 단계",
            "model": "gemma4:31b",
        },
        {
            "normalized_text": "원고",
            "contextual_decision_logs": [{"decision": "deferred"}],
            "model": "gemma4:31b",
        },
    ),
)
def test_transform_request_requires_only_integrated_fields(payload: dict) -> None:
    with pytest.raises(ValidationError):
        LLMTransformRequest.model_validate(payload)


def test_transform_rejects_unsupported_model(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "run_llm_stage_binary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            LLMStageRuntimeError(
                "Unsupported LLM model.",
                status_code=400,
                detail="Unsupported LLM model.",
            )
        ),
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMTransformRequest(
                normalized_text="원고",
                model="unknown",
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported LLM model."


def test_llm_transform_uses_stage_binary(monkeypatch) -> None:
    captured = {}

    def fake_run_llm_stage_binary(normalized_text, *, model=None):
        captured["normalized_text"] = normalized_text
        captured["model"] = model
        return {
            "speech_text": "궁무른, 조씀니다.",
            "model": model or "gemma4:31b",
            "elapsed_ms": 1234.5678,
        }

    monkeypatch.setattr(
        server_module,
        "run_llm_stage_binary",
        fake_run_llm_stage_binary,
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    result = endpoint(
        LLMTransformRequest(
            normalized_text="국물은 좋습니다.",
            model="gemma4:e4b",
        )
    )

    assert result == {
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemma4:e4b",
        "elapsed_ms": 1234.568,
    }
    assert captured == {
        "normalized_text": "국물은 좋습니다.",
        "model": "gemma4:e4b",
    }


def test_llm_transform_uses_default_model_when_omitted(monkeypatch) -> None:
    captured = {}

    def fake_run_llm_stage_binary(normalized_text, *, model=None):
        captured["model"] = model
        return {
            "speech_text": "원고",
            "model": "gemma4:31b",
            "elapsed_ms": 1.0,
        }

    monkeypatch.setattr(
        server_module,
        "run_llm_stage_binary",
        fake_run_llm_stage_binary,
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    result = endpoint(LLMTransformRequest(normalized_text="원고"))

    assert result["model"] == "gemma4:31b"
    assert captured["model"] is None


def test_contract_violation_maps_to_bad_gateway(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "run_llm_stage_binary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            LLMStageRuntimeError(
                "LLM response deleted or reordered existing whitespace, "
                "line breaks, or fixed punctuation.",
                status_code=502,
                detail={
                    "message": (
                        "LLM response deleted or reordered existing whitespace, "
                        "line breaks, or fixed punctuation."
                    ),
                    "stage": "speech",
                    "speech_text": "다른 원고",
                },
            )
        ),
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMTransformRequest(
                normalized_text="원고.",
                model="gemma4:e4b",
            )
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == {
        "message": (
            "LLM response deleted or reordered existing whitespace, "
            "line breaks, or fixed punctuation."
        ),
        "stage": "speech",
        "speech_text": "다른 원고",
    }


def test_missing_configuration_maps_to_service_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "run_llm_stage_binary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            LLMStageRuntimeError(
                "Required environment variable VLLM_BASE_URL is missing.",
                status_code=503,
                detail="Required environment variable VLLM_BASE_URL is missing.",
            )
        ),
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            LLMTransformRequest(
                normalized_text="원고",
                model="gemma4-31B-it (vLLM)",
            )
        )

    assert exc_info.value.status_code == 503
    assert "VLLM_BASE_URL" in exc_info.value.detail


def test_binary_runtime_failure_maps_to_bad_gateway(monkeypatch) -> None:
    monkeypatch.setattr(
        server_module,
        "run_llm_stage_binary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            BinaryRuntimeError("LLM stage binary returned empty output")
        ),
    )
    endpoint = get_endpoint("/api/llm/transform", "POST")

    with pytest.raises(HTTPException) as exc_info:
        endpoint(LLMTransformRequest(normalized_text="원고"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "LLM stage binary returned empty output"
