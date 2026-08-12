from __future__ import annotations

import pytest

from LLM import stage_engine
from LLM.client import GenerationResult
from LLM.response_validation import LLMStageContractError


def test_stage_engine_runs_only_from_normalized_text(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured = {}

    def fake_generate(*, model, prompt, settings):
        captured["model"] = model
        captured["prompt"] = prompt
        return GenerationResult(text="궁무른, 조씀니다.", elapsed_ms=12.5)

    monkeypatch.setattr(stage_engine, "generate", fake_generate)

    result = stage_engine.transform("국물은 좋습니다.", model="gemma4:e4b")

    assert result.speech_text == "궁무른, 조씀니다."
    assert result.model == "gemma4:e4b"
    assert result.elapsed_ms == 12.5
    assert "<NORMALIZED_TEXT>\n국물은 좋습니다.\n</NORMALIZED_TEXT>" in captured[
        "prompt"
    ]
    assert captured["model"] == "gemma4:e4b"


def test_stage_engine_rejects_changed_confirmed_news_without_stage1_dependency(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    monkeypatch.setattr(
        stage_engine,
        "generate",
        lambda **_kwargs: GenerationResult(
            text="오늘 뉴스 보도입니다.", elapsed_ms=1.0
        ),
    )

    with pytest.raises(LLMStageContractError, match="confirmed news"):
        stage_engine.transform("오늘 news 보도입니다.", model="gemma4:e4b")


def test_stage_engine_runtime_asset_check_requires_no_llm_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)

    stage_engine.validate_runtime_assets()
