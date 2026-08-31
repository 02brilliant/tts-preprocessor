from __future__ import annotations

from argparse import Namespace
import json

import pytest

from LLM.cli_protocol import classify_llm_stage_error
from LLM.config import ConfigurationError
from LLM.response_validation import LLMStageContractError
from LLM.validation_models import ValidationIssue
from LLM.stage_engine import UnsupportedLLMModelError
from LLM.vllm_client import VllmTimeoutError
from bin import integrated_llm_cli as entrypoint
from engine.span_engine.models import TransformOutput


def test_classify_supported_failures() -> None:
    assert classify_llm_stage_error(UnsupportedLLMModelError("Unsupported LLM model.")) == (400, "Unsupported LLM model.")
    status, detail = classify_llm_stage_error(ConfigurationError("Required environment variable VLLM_BASE_URL is missing."))
    assert status == 503 and "VLLM_BASE_URL" in detail
    assert classify_llm_stage_error(VllmTimeoutError("timed out")) == (504, "timed out")


def test_classify_contract_violation_preserves_output() -> None:
    status, detail = classify_llm_stage_error(LLMStageContractError("invalid", stage="speech", output_text="원출력"))
    assert status == 502
    assert detail == {"message": "invalid", "stage": "speech", "speech_text": "원출력"}


def test_classify_residual_contract_violation_includes_output_range() -> None:
    status, detail = classify_llm_stage_error(
        LLMStageContractError(
            "residual",
            stage="speech",
            output_text="약 2조 원",
            code="RESIDUAL_SPEECH_SURFACE",
            severity="Medium",
            output_start=2,
            output_end=3,
        )
    )
    assert status == 502
    assert detail["validation_failure"]["output_start"] == 2
    assert detail["validation_failure"]["output_end"] == 3


def _args(**overrides) -> Namespace:
    values = dict(input=None, output=None, text=None, model=None, json=False, list_models=False, check=False)
    values.update(overrides)
    return Namespace(**values)


def test_integrated_entrypoint_lists_models(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entrypoint, "parse_args", lambda *, stage_level: _args(list_models=True))
    assert entrypoint.run(stage_level=3, prompt_level=1) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["default_model"] in payload["models"]


def test_integrated_entrypoint_self_check_uses_current_hyphen_policy(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _args(check=True, json=True),
    )
    monkeypatch.setattr("LLM.stage_engine.validate_runtime_assets", lambda **_kwargs: None)
    monkeypatch.setattr(
        "engine.main.transform_output",
        lambda text: TransformOutput("에이비씨와 삼-킬로그램", [], None),
    )

    assert entrypoint.run(stage_level=3, prompt_level=1) == 0
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "ready": True,
        "level": 3,
    }


def test_integrated_entrypoint_self_check_reports_expected_and_actual(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _args(check=True),
    )
    monkeypatch.setattr("LLM.stage_engine.validate_runtime_assets", lambda **_kwargs: None)
    monkeypatch.setattr(
        "engine.main.transform_output",
        lambda text: TransformOutput("에이비씨와 삼 킬로그램", [], None),
    )

    assert entrypoint.run(stage_level=4, prompt_level=2) == 1
    error = capsys.readouterr().err
    assert "expected='에이비씨와 삼-킬로그램'" in error
    assert "actual='에이비씨와 삼 킬로그램'" in error


def test_integrated_entrypoint_runs_full_rules_once_then_fixed_prompt(monkeypatch, capsys) -> None:
    calls = []

    class FakeResult:
        speech_text = "궁무른, 조씀니다."
        model = "gemma4:e4b"
        elapsed_ms = 12.3456
        validation_fallback = False

    def fake_rules(text):
        calls.append(("rules", text))
        return TransformOutput("국물은 매우 좋습니다.", [], None)

    def fake_llm(text, *, model=None, prompt_level=1, snapshot=None):
        calls.append(("llm", text, model, prompt_level))
        return FakeResult()

    monkeypatch.setattr(entrypoint, "parse_args", lambda *, stage_level: _args(text="원문", model="gemma4:e4b", json=True))
    monkeypatch.setattr("engine.main.transform_output", fake_rules)
    monkeypatch.setattr("LLM.stage_engine.transform", fake_llm)
    timings = iter((1.0, 1.004, 2.0, 2.015))
    monkeypatch.setattr(entrypoint.time, "perf_counter", lambda: next(timings))

    assert entrypoint.run(stage_level=4, prompt_level=2) == 0
    assert calls == [("rules", "원문"), ("llm", "국물은 매우 좋습니다.", "gemma4:e4b", 2)]
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "level": 4,
        "normalized_text": "국물은 매우 좋습니다.",
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemma4:e4b",
        "elapsed_ms": 12.346,
        "rule_elapsed_ms": 4.0,
        "llm_elapsed_ms": 15.0,
        "llm_called": True,
        "llm_skip_reason": None,
    }


def test_integrated_entrypoint_skips_llm_after_rules_once(monkeypatch, capsys) -> None:
    calls = []

    def fake_rules(text):
        calls.append(("rules", text))
        return TransformOutput("삼 킬로그램", [], None)

    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _args(text="3kg", model="gemma4:e4b", json=True),
    )
    monkeypatch.setattr("engine.main.transform_output", fake_rules)
    monkeypatch.setattr(
        "LLM.stage_engine.transform",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("LLM must not run")
        ),
    )
    timings = iter((1.0, 1.002))
    monkeypatch.setattr(entrypoint.time, "perf_counter", lambda: next(timings))

    assert entrypoint.run(stage_level=3, prompt_level=1) == 0
    assert calls == [("rules", "3kg")]
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "level": 3,
        "normalized_text": "삼 킬로그램",
        "speech_text": "삼 킬로그램",
        "model": "gemma4:e4b",
        "elapsed_ms": 0.0,
        "rule_elapsed_ms": 2.0,
        "llm_elapsed_ms": 0.0,
        "llm_called": False,
        "llm_skip_reason": "short_simple_rule_complete",
    }


def test_integrated_entrypoint_error_includes_rule_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entrypoint, "parse_args", lambda *, stage_level: _args(text="원문", model="unknown", json=True))
    monkeypatch.setattr("engine.main.transform_output", lambda text: TransformOutput("규칙 결과", [], None))
    monkeypatch.setattr("LLM.stage_engine.transform", lambda *_args, **_kwargs: (_ for _ in ()).throw(UnsupportedLLMModelError("Unsupported LLM model.")))
    assert entrypoint.run(stage_level=3, prompt_level=1) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload == {"ok": False, "status": 400, "detail": "Unsupported LLM model.", "normalized_text": "규칙 결과"}


def test_level4_fixed_overlay_runs_without_llm_and_preserves_normalized_text(
    monkeypatch,
    capsys,
) -> None:
    calls = []

    class FakeResult:
        speech_text = "unexpected"
        model = "gemma4:e4b"
        elapsed_ms = 3.0
        validation_fallback = False

    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _args(text="생산량은 늘었습니다.", model="gemma4:e4b", json=True),
    )
    monkeypatch.setattr(
        "engine.main.transform_output",
        lambda text: TransformOutput(text, [], None),
    )

    def fake_llm(text, *, model=None, prompt_level=1, snapshot=None):
        calls.append((text, prompt_level, snapshot.normalized_text))
        return FakeResult()

    monkeypatch.setattr("LLM.stage_engine.transform", fake_llm)
    assert entrypoint.run(stage_level=4, prompt_level=2) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["level"] == 4
    assert payload["normalized_text"] == "생산량은 늘었습니다."
    assert payload["speech_text"] == "생산냥은 늘었습니다."
    assert payload["llm_called"] is False
    assert calls == []


def test_level4_exposes_rejected_llm_output_with_safe_fallback(
    monkeypatch,
    capsys,
) -> None:
    class FakeResult:
        speech_text = "가격은 삼쩜영오 달러입니다."
        model = "gemma4:e4b"
        elapsed_ms = 3.0
        validation_fallback = True
        rejected_speech_text = "가격은 삼점영오 달러입니다."

        validation_issues = (
            ValidationIssue(
                "LOCKED_READING_MUTATION",
                "Critical",
                "LLM response changed a rule-engine locked reading.",
            ),
        )

    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _args(
            text="가격은 3.05달러입니다.", model="gemma4:e4b", json=True
        ),
    )
    monkeypatch.setattr(
        "engine.main.transform_output",
        lambda text: TransformOutput("가격은 삼쩜영오 달러입니다.", [], None),
    )
    monkeypatch.setattr("LLM.stage_engine.transform", lambda *_args, **_kwargs: FakeResult())

    assert entrypoint.run(stage_level=4, prompt_level=2) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["speech_text"] == "가격은 삼쩜영오 달러입니다."
    assert payload["rejected_speech_text"] == "가격은 삼점영오 달러입니다."
    assert payload["validation_failure"] == {
        "code": "LOCKED_READING_MUTATION",
        "severity": "Critical",
        "message": "LLM response changed a rule-engine locked reading.",
    }
