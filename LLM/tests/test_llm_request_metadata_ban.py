"""LLM requests must not carry rule-engine decision metadata.

Policy: the optional LLM receives only the ordinary normalized/overlay text
string. contextual_decision_logs, candidates, and decision markers must not be
attached to the model prompt or generate() kwargs.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from LLM import stage_engine
from LLM.client import GenerationResult
from LLM.prompt_template import build_prompt
from bin import integrated_llm_cli as entrypoint
from engine.main import transform as rule_transform
from engine.span_engine.models import TransformOutput


FORBIDDEN_METADATA_MARKERS = (
    "contextual_decision_logs",
    "candidate_readings",
    "decision_markers",
    "CONTEXTUAL_DECISION",
    "DECISION_CANDIDATES",
    "blocking_reason",
    "reentry_blocked",
)


def _assert_prompt_has_no_decision_metadata(prompt: str) -> None:
    for marker in FORBIDDEN_METADATA_MARKERS:
        assert marker not in prompt, marker
    assert "<CONTEXTUAL_DECISION_LOGS>" not in prompt
    assert "<DECISION_CANDIDATES>" not in prompt


@pytest.mark.parametrize("prompt_level", (1, 2))
def test_build_prompt_rejects_decision_metadata_tags(prompt_level: int) -> None:
    normalized_text = "3번 확인했고 5분이 남았다."
    rendered = build_prompt(normalized_text, prompt_level=prompt_level)
    assert f"<NORMALIZED_TEXT>\n{normalized_text}\n</NORMALIZED_TEXT>" in rendered
    _assert_prompt_has_no_decision_metadata(rendered)


def test_build_prompt_from_rule_output_stays_plain_reading() -> None:
    normalized = rule_transform("3번 확인")
    rendered = build_prompt(normalized, prompt_level=1)
    assert f"<NORMALIZED_TEXT>\n{normalized}\n</NORMALIZED_TEXT>" in rendered
    _assert_prompt_has_no_decision_metadata(rendered)
    assert "contextual_decision_logs" not in normalized


@pytest.mark.parametrize("prompt_level", (1, 2))
def test_stage_engine_generate_kwargs_exclude_decision_metadata(
    prompt_level: int, monkeypatch
) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured: dict = {}

    def fake_generate_safe(*, model, prompt, settings):
        captured["kwargs"] = {"model": model, "prompt": prompt, "settings": settings}
        start = prompt.index("<NORMALIZED_TEXT>\n") + len("<NORMALIZED_TEXT>\n")
        end = prompt.index("\n</NORMALIZED_TEXT>")
        text = prompt[start:end]
        return GenerationResult(text=text, elapsed_ms=1.0)

    monkeypatch.setattr(stage_engine, "generate", fake_generate_safe)

    normalized = "국물은 좋습니다."
    result = stage_engine.transform(
        normalized,
        model="gemma4:e4b",
        prompt_level=prompt_level,
    )

    assert result.speech_text == normalized
    assert set(captured["kwargs"]) == {"model", "prompt", "settings"}
    for forbidden in (
        "contextual_decision_logs",
        "candidates",
        "decision_markers",
        "trace",
        "debug",
    ):
        assert forbidden not in captured["kwargs"]
    _assert_prompt_has_no_decision_metadata(captured["kwargs"]["prompt"])
    assert (
        f"<NORMALIZED_TEXT>\n{normalized}\n</NORMALIZED_TEXT>"
        in captured["kwargs"]["prompt"]
    )


def _cli_args(**overrides) -> Namespace:
    values = dict(
        input=None,
        output=None,
        text=None,
        model=None,
        json=False,
        list_models=False,
        check=False,
    )
    values.update(overrides)
    return Namespace(**values)


@pytest.mark.parametrize(("stage_level", "prompt_level"), ((3, 1), (4, 2)))
def test_integrated_cli_passes_only_overlay_text_to_llm(
    stage_level: int, prompt_level: int, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        entrypoint,
        "parse_args",
        lambda *, stage_level: _cli_args(text="국물은 좋습니다.", json=True),
    )
    monkeypatch.setattr(
        "engine.main.transform_output",
        lambda text: TransformOutput("국물은 좋습니다.", [], None),
    )
    monkeypatch.setattr(
        "LLM.pronunciation_overlay.apply_pronunciation_overlay",
        lambda text, *, stage, snapshot: type(
            "Overlay",
            (),
            {"text": text, "snapshot": snapshot},
        )(),
    )
    monkeypatch.setattr(
        "LLM.invocation_gate.decide_llm_invocation",
        lambda text, *, stage_level: type(
            "Decision",
            (),
            {"call_llm": True, "reason": None},
        )(),
    )

    captured: dict = {}

    def fake_transform_llm(text, *, model=None, prompt_level=1, snapshot=None):
        captured["text"] = text
        captured["model"] = model
        captured["prompt_level"] = prompt_level
        captured["kwarg_names"] = {"text", "model", "prompt_level", "snapshot"}
        return type(
            "Result",
            (),
            {
                "speech_text": text,
                "model": model or "gemma4:e4b",
                "elapsed_ms": 1.5,
                "validation_fallback": False,
                "validation_issues": (),
                "rejected_speech_text": None,
            },
        )()

    monkeypatch.setattr("LLM.stage_engine.transform", fake_transform_llm)

    assert entrypoint.run(stage_level=stage_level, prompt_level=prompt_level) == 0
    payload = json.loads(capsys.readouterr().out)

    assert captured["text"] == "국물은 좋습니다."
    assert captured["prompt_level"] == prompt_level
    assert "contextual_decision_logs" not in captured
    assert payload["normalized_text"] == "국물은 좋습니다."
    assert payload["speech_text"] == "국물은 좋습니다."
    for marker in FORBIDDEN_METADATA_MARKERS:
        assert marker not in json.dumps(payload, ensure_ascii=False)


def test_stage_engine_and_cli_sources_do_not_wire_decision_logs_into_generate() -> None:
    stage_source = Path("LLM/stage_engine.py").read_text(encoding="utf-8")
    cli_source = Path("bin/integrated_llm_cli.py").read_text(encoding="utf-8")

    for source in (stage_source, cli_source):
        assert "contextual_decision_logs" not in source
        assert "candidate_readings" not in source
