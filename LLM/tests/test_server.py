from __future__ import annotations

from pydantic import ValidationError
import pytest

from api import server as server_module
from api.binary_runtime import LLMStageRuntimeError
from api.server import TransformRequest, app


@pytest.fixture(autouse=True)
def reset_llm_resilience_state():
    server_module._reset_llm_resilience_state_for_tests()
    yield
    server_module._reset_llm_resilience_state_for_tests()


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


def test_integrated_provider_error_returns_rules_only_fallback(monkeypatch) -> None:
    calls = []

    def fake_run(text, *, level, model=None, rules_only=False):
        calls.append(rules_only)
        if not rules_only:
            raise LLMStageRuntimeError(
                "invalid",
                status_code=502,
                detail={"message": "invalid", "normalized_text": "규칙 결과"},
            )
        return {
            "normalized_text": "규칙 결과",
            "speech_text": "삼단계 확정 결과",
            "model": model or "m",
            "elapsed_ms": 0.0,
            "rule_elapsed_ms": 2.0,
            "llm_elapsed_ms": 0.0,
            "llm_called": False,
            "llm_skip_reason": "rules_only_requested",
            "llm_status": "rules_only",
            "fallback_used": True,
            "fallback_reason": "RULES_ONLY_REQUESTED",
        }

    monkeypatch.setattr(server_module, "run_integrated_binary", fake_run)
    result = get_endpoint("/api/transform", "POST")(
        TransformRequest(text="원문", level=3, model="m")
    )

    assert calls == [False, True]
    assert result["speech_text"] == "삼단계 확정 결과"
    assert result["llm_status"] == "unavailable"
    assert result["fallback_reason"] == "LLM_UPSTREAM_UNAVAILABLE"


def test_circuit_breaker_skips_llm_after_repeated_failures(monkeypatch) -> None:
    calls = []

    def fake_run(text, *, level, model=None, rules_only=False):
        calls.append(rules_only)
        return {
            "normalized_text": "규칙 결과",
            "speech_text": "오단계 확정 결과",
            "model": model or "m",
            "elapsed_ms": 1.0 if not rules_only else 0.0,
            "rule_elapsed_ms": 2.0,
            "llm_elapsed_ms": 1.0 if not rules_only else 0.0,
            "llm_called": not rules_only,
            "llm_skip_reason": "rules_only_requested" if rules_only else None,
            "llm_status": "rules_only" if rules_only else "timeout",
            "fallback_used": True,
            "fallback_reason": (
                "RULES_ONLY_REQUESTED" if rules_only else "LLM_UPSTREAM_TIMEOUT"
            ),
        }

    monkeypatch.setattr(server_module, "run_integrated_binary", fake_run)
    results = [
        server_module.transform_request_payload(
            {"text": "원문", "level": 5, "model": "m"}
        )
        for _ in range(4)
    ]

    assert calls == [False, False, False, True]
    assert results[-1]["llm_status"] == "circuit_open"
    assert results[-1]["speech_text"] == "오단계 확정 결과"


def test_overload_uses_rules_only_without_waiting(monkeypatch) -> None:
    server_module._LLM_ACTIVE_CALLS["m"] = server_module._LLM_MAX_INFLIGHT_PER_MODEL
    calls = []

    def fake_run(text, *, level, model=None, rules_only=False):
        calls.append(rules_only)
        return {
            "normalized_text": "규칙 결과",
            "speech_text": "사단계 확정 결과",
            "model": model or "m",
            "elapsed_ms": 0.0,
            "rule_elapsed_ms": 2.0,
            "llm_elapsed_ms": 0.0,
            "llm_called": False,
            "llm_skip_reason": "rules_only_requested",
            "llm_status": "rules_only",
            "fallback_used": True,
            "fallback_reason": "RULES_ONLY_REQUESTED",
        }

    monkeypatch.setattr(server_module, "run_integrated_binary", fake_run)
    result = server_module.transform_request_payload(
        {"text": "원문", "level": 4, "model": "m"}
    )

    assert calls == [True]
    assert result["llm_status"] == "overloaded"
    assert result["fallback_reason"] == "LLM_CONCURRENCY_LIMIT"


def test_levels_zero_to_two_do_not_use_integrated_binary(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "run_integrated_binary", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not run")))
    monkeypatch.setattr(server_module, "run_transform_binary", lambda text, **kwargs: f"{kwargs.get('profile', 'default')}:{text}")
    assert server_module.transform_request_payload({"text": "원문", "level": 0}) == {"normalized_text": "원문"}
    assert server_module.transform_request_payload({"text": "원문", "level": 1})["normalized_text"] == "simplified:원문"
    assert server_module.transform_request_payload({"text": "원문", "level": 2})["normalized_text"] == "default:원문"
