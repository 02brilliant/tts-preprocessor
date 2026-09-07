from __future__ import annotations

from fastapi import HTTPException
from pydantic import ValidationError
import pytest

from api import server as server_module
from api.binary_runtime import LLMStageRuntimeError
from api.server import TransformRequest, app


def get_endpoint(path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Missing route: {method} {path}")


def test_public_routes_expose_one_transform_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "list_llm_models", lambda: {"models": ["m"], "default_model": "m"})
    assert get_endpoint("/api/transform", "POST")
    assert get_endpoint("/api/llm/models", "GET")() == {"models": ["m"], "default_model": "m"}
    with pytest.raises(AssertionError):
        get_endpoint("/api/llm/transform", "POST")


@pytest.mark.parametrize("level", (False, "3", -1, 6))
def test_request_rejects_invalid_levels(level) -> None:
    with pytest.raises(ValidationError):
        TransformRequest.model_validate({"text": "원고", "level": level})


def test_request_limits_model_to_llm_levels() -> None:
    with pytest.raises(ValidationError):
        TransformRequest(text="원고", level=2, model="m")


@pytest.mark.parametrize("level", (3, 4, 5))
def test_transform_uses_one_integrated_binary(level, monkeypatch) -> None:
    calls = []

    def fake_run(text, *, level, model=None):
        calls.append((text, level, model))
        return {"normalized_text": "규칙 결과", "speech_text": "발화 결과", "model": model or "m", "elapsed_ms": 1.25, "rule_elapsed_ms": 2.5, "llm_elapsed_ms": 3.75, "llm_called": True, "llm_skip_reason": None}

    monkeypatch.setattr(server_module, "run_integrated_binary", fake_run)
    result = get_endpoint("/api/transform", "POST")(TransformRequest(text="원문", level=level, model="m"))
    assert result == {"normalized_text": "규칙 결과", "speech_text": "발화 결과", "model": "m", "elapsed_ms": 1.25, "rule_elapsed_ms": 2.5, "llm_elapsed_ms": 3.75, "llm_called": True, "llm_skip_reason": None}
    assert calls == [("원문", level, "m")]


def test_integrated_error_status_and_normalized_output_are_preserved(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "run_integrated_binary", lambda *_args, **_kwargs: (_ for _ in ()).throw(LLMStageRuntimeError("invalid", status_code=502, detail={"message": "invalid", "normalized_text": "규칙 결과", "speech_text": "원출력"})))
    with pytest.raises(HTTPException) as exc_info:
        get_endpoint("/api/transform", "POST")(TransformRequest(text="원문", level=3))
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["normalized_text"] == "규칙 결과"


def test_levels_zero_to_two_do_not_use_integrated_binary(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "run_integrated_binary", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not run")))
    monkeypatch.setattr(server_module, "run_transform_binary", lambda text, **kwargs: f"{kwargs.get('profile', 'default')}:{text}")
    assert server_module.transform_request_payload({"text": "원문", "level": 0}) == {"normalized_text": "원문"}
    assert server_module.transform_request_payload({"text": "원문", "level": 1})["normalized_text"] == "simplified:원문"
    assert server_module.transform_request_payload({"text": "원문", "level": 2})["normalized_text"] == "default:원문"
