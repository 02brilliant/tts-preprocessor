from __future__ import annotations

import threading

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
        return GenerationResult(text="국물은, 좋습니다.", elapsed_ms=12.5)

    monkeypatch.setattr(stage_engine, "generate", fake_generate)

    result = stage_engine.transform("국물은 좋습니다.", model="gemma4:e4b")

    assert result.speech_text == "국물은, 좋습니다."
    assert result.model == "gemma4:e4b"
    assert result.elapsed_ms == 12.5
    assert "<NORMALIZED_TEXT>\n국물은 좋습니다.\n</NORMALIZED_TEXT>" in captured[
        "prompt"
    ]
    assert captured["model"] == "gemma4:e4b"


def test_stage_engine_uses_natural_speech_prompt_for_level_two(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured = {}

    def fake_generate(*, model, prompt, settings):
        captured["prompt"] = prompt
        return GenerationResult(text="현장에 있는 기잡니다.", elapsed_ms=2.0)

    monkeypatch.setattr(stage_engine, "generate", fake_generate)

    result = stage_engine.transform(
        "현장에 있는 기자입니다.",
        model="gemma4:e4b",
        prompt_level=2,
    )

    assert result.speech_text == "현장에 있는 기잡니다."
    assert "<NATURAL_SPEECH_CONTRACTION>" in captured["prompt"]


def test_level5_validation_failure_falls_back_without_retry(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    calls = 0

    def fake_generate(*, model, prompt, settings):
        nonlocal calls
        calls += 1
        return GenerationResult(text="궁무른 가치 읻씀니다.", elapsed_ms=2.0)

    monkeypatch.setattr(stage_engine, "generate", fake_generate)
    result = stage_engine.transform(
        "국물은 같이 있습니다.",
        model="gemma4:e4b",
        prompt_level=3,
    )
    assert result.speech_text == "국물은 같이 있습니다."
    assert result.validation_fallback is True
    assert result.validation_issues[0].code == "UNEXPECTED_KOREAN_REWRITE"
    assert calls == 1


def test_stage_engine_rejects_changed_confirmed_kbs_news_without_stage1_dependency(
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

    with pytest.raises(LLMStageContractError, match="confirmed KBS news"):
        stage_engine.transform("KBS news 보도입니다.", model="gemma4:e4b")


def test_stage_engine_rejects_new_stage1_time_frame_comma(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    monkeypatch.setattr(
        stage_engine,
        "generate",
        lambda **_kwargs: GenerationResult(
            text="올해 상반기, 매출이 늘었습니다.", elapsed_ms=1.0
        ),
    )

    with pytest.raises(LLMStageContractError, match="time-frame"):
        stage_engine.transform(
            "올해 상반기 매출이 늘었습니다.",
            model="gemma4:e4b",
        )


def test_stage_engine_routes_vllm_model_to_vllm_client(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    captured = {}

    def fake_generate_vllm(*, model, prompt, settings):
        captured["model"] = model
        captured["base_url"] = settings.base_url
        return GenerationResult(text="국물은, 좋습니다.", elapsed_ms=8.0)

    monkeypatch.setattr(stage_engine, "generate_vllm", fake_generate_vllm)

    result = stage_engine.transform(
        "국물은 좋습니다.",
        model="gemma4-31B-it (vLLM)",
    )

    assert result.speech_text == "국물은, 좋습니다."
    assert result.model == "gemma4-31B-it (vLLM)"
    assert result.elapsed_ms == 8.0
    assert captured == {
        "model": "google/gemma-4-31B-it",
        "base_url": "http://vllm.invalid/v1",
    }


def test_stage_engine_runs_vllm_paragraphs_concurrently(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    captured = {"prompts": [], "max_inflight": 0}
    inflight = 0
    lock = threading.Lock()
    barrier = threading.Barrier(2, timeout=2)

    def fake_generate_vllm(*, model, prompt, settings):
        nonlocal inflight
        captured["prompts"].append(prompt)
        with lock:
            inflight += 1
            captured["max_inflight"] = max(captured["max_inflight"], inflight)
        barrier.wait()
        with lock:
            inflight -= 1
        if "국물은 좋습니다." in prompt:
            return GenerationResult(text="국물은, 좋습니다.", elapsed_ms=40.0)
        if "밥은 따뜻합니다." in prompt:
            return GenerationResult(text="밥은, 따뜻합니다.", elapsed_ms=50.0)
        raise AssertionError(f"unexpected prompt: {prompt}")

    monkeypatch.setattr(stage_engine, "generate_vllm", fake_generate_vllm)

    result = stage_engine.transform(
        "국물은 좋습니다.\n\n밥은 따뜻합니다.",
        model="gemma4-31B-it (vLLM)",
    )

    assert result.speech_text == "국물은, 좋습니다.\n\n밥은, 따뜻합니다."
    assert result.model == "gemma4-31B-it (vLLM)"
    assert captured["max_inflight"] == 2
    assert len(captured["prompts"]) == 2
    assert any("국물은 좋습니다." in prompt for prompt in captured["prompts"])
    assert any("밥은 따뜻합니다." in prompt for prompt in captured["prompts"])


def test_stage_engine_runtime_asset_check_requires_no_llm_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)

    stage_engine.validate_runtime_assets()
