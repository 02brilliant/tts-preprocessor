from __future__ import annotations

from argparse import Namespace
import json

from LLM.cli_protocol import classify_llm_stage_error
from LLM.config import ConfigurationError
from LLM.response_validation import LLMStageContractError
from LLM.stage_engine import UnsupportedLLMModelError
from LLM.vllm_client import VllmTimeoutError
from bin import integrated_llm_cli as entrypoint


def test_classify_supported_failures() -> None:
    assert classify_llm_stage_error(UnsupportedLLMModelError("Unsupported LLM model.")) == (400, "Unsupported LLM model.")
    status, detail = classify_llm_stage_error(ConfigurationError("Required environment variable VLLM_BASE_URL is missing."))
    assert status == 503 and "VLLM_BASE_URL" in detail
    assert classify_llm_stage_error(VllmTimeoutError("timed out")) == (504, "timed out")


def test_classify_contract_violation_preserves_output() -> None:
    status, detail = classify_llm_stage_error(LLMStageContractError("invalid", stage="speech", output_text="원출력"))
    assert status == 502
    assert detail == {"message": "invalid", "stage": "speech", "speech_text": "원출력"}


def _args(**overrides) -> Namespace:
    values = dict(input=None, output=None, text=None, model=None, json=False, list_models=False, check=False)
    values.update(overrides)
    return Namespace(**values)


def test_integrated_entrypoint_lists_models(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entrypoint, "parse_args", lambda *, stage_level: _args(list_models=True))
    assert entrypoint.run(stage_level=3, prompt_level=1) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["default_model"] in payload["models"]


def test_integrated_entrypoint_runs_full_rules_once_then_fixed_prompt(monkeypatch, capsys) -> None:
    calls = []

    class FakeResult:
        speech_text = "궁무른, 조씀니다."
        model = "gemma4:e4b"
        elapsed_ms = 12.3456

    def fake_rules(text):
        calls.append(("rules", text))
        return "국물은 매우 좋습니다."

    def fake_llm(text, *, model=None, prompt_level=1):
        calls.append(("llm", text, model, prompt_level))
        return FakeResult()

    monkeypatch.setattr(entrypoint, "parse_args", lambda *, stage_level: _args(text="원문", model="gemma4:e4b", json=True))
    monkeypatch.setattr("engine.main.transform", fake_rules)
    monkeypatch.setattr("LLM.stage_engine.transform", fake_llm)

    assert entrypoint.run(stage_level=4, prompt_level=2) == 0
    assert calls == [("rules", "원문"), ("llm", "국물은 매우 좋습니다.", "gemma4:e4b", 2)]
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "level": 4,
        "normalized_text": "국물은 매우 좋습니다.",
        "speech_text": "궁무른, 조씀니다.",
        "model": "gemma4:e4b",
        "elapsed_ms": 12.346,
        "llm_called": True,
        "llm_skip_reason": None,
    }


def test_integrated_entrypoint_skips_llm_after_rules_once(monkeypatch, capsys) -> None:
    calls = []

    def fake_rules(text):
        calls.append(("rules", text))
        return "삼 킬로그램"

    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _args(text="3kg", model="gemma4:e4b", json=True),
    )
    monkeypatch.setattr("engine.main.transform", fake_rules)
    monkeypatch.setattr(
        "LLM.stage_engine.transform",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("LLM must not run")
        ),
    )

    assert entrypoint.run(stage_level=3, prompt_level=1) == 0
    assert calls == [("rules", "3kg")]
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "level": 3,
        "normalized_text": "삼 킬로그램",
        "speech_text": "삼 킬로그램",
        "model": "gemma4:e4b",
        "elapsed_ms": 0.0,
        "llm_called": False,
        "llm_skip_reason": "short_simple_rule_complete",
    }


def test_integrated_entrypoint_error_includes_rule_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entrypoint, "parse_args", lambda *, stage_level: _args(text="원문", model="unknown", json=True))
    monkeypatch.setattr("engine.main.transform", lambda text: "규칙 결과")
    monkeypatch.setattr("LLM.stage_engine.transform", lambda *_args, **_kwargs: (_ for _ in ()).throw(UnsupportedLLMModelError("Unsupported LLM model.")))
    assert entrypoint.run(stage_level=3, prompt_level=1) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload == {"ok": False, "status": 400, "detail": "Unsupported LLM model.", "normalized_text": "규칙 결과"}
