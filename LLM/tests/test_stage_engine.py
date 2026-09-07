from __future__ import annotations

import json
import re
import threading

import pytest

from LLM import stage_engine
from LLM.client import GenerationResult
from LLM.response_validation import LLMStageContractError
from LLM.stage5_preprocessor import build_stage5_work_plan


def _select_kind(prompt: str, kind: str) -> str:
    match = re.search(
        r"<STAGE[345]_WORK_PLAN>\n(?P<plan>.*?)\n</STAGE[345]_WORK_PLAN>",
        prompt,
        re.DOTALL,
    )
    assert match is not None
    plan = json.loads(match.group("plan"))
    candidate = next(item for item in plan["candidates"] if item["kind"] == kind)
    return json.dumps(
        {
            "schema_version": 1,
            "decisions": [{"id": candidate["id"], "option": 0}],
        }
    )


def test_stage_engine_runs_only_from_normalized_text(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured = {}

    def fake_generate(*, model, prompt, settings):
        captured["model"] = model
        captured["prompt"] = prompt
        return GenerationResult(text='{"schema_version":1,"decisions":[]}', elapsed_ms=12.5)

    monkeypatch.setattr(stage_engine, "generate", fake_generate)

    result = stage_engine.transform("국물은 좋습니다.", model="gemma4:e4b")

    assert result.speech_text == "국물은 좋습니다."
    assert result.validation_fallback is False
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
        return GenerationResult(
            text=_select_kind(prompt, "natural_speech_contraction"),
            elapsed_ms=2.0,
        )

    monkeypatch.setattr(stage_engine, "generate", fake_generate)

    result = stage_engine.transform(
        "현장에 있는 기자입니다.",
        model="gemma4:e4b",
        prompt_level=2,
    )

    assert result.speech_text == "현장에 있는 기잡니다."
    assert "<NATURAL_SPEECH_CONTRACTION>" in captured["prompt"]
    assert "<STAGE4_WORK_PLAN>" in captured["prompt"]


def test_level4_validation_failure_falls_back_without_retry(monkeypatch) -> None:
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
        prompt_level=2,
    )
    assert result.speech_text == "국물은 같이 있습니다."
    assert result.validation_fallback is True
    assert result.validation_issues[0].code == "INVALID_SELECTION_RESPONSE"
    assert result.rejected_speech_text == "궁무른 가치 읻씀니다."
    assert calls == 1


def test_level5_uses_standard_prompt_and_accepts_closed_candidate(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    captured = {}

    def fake_generate(*, model, prompt, settings):
        captured["prompt"] = prompt
        return GenerationResult(
            text=_select_kind(prompt, "contextual_standard_pronunciation"),
            elapsed_ms=2.0,
        )

    monkeypatch.setattr(stage_engine, "generate", fake_generate)
    result = stage_engine.transform(
        "그 대가는 컸습니다.",
        model="gemma4:e4b",
        prompt_level=3,
    )

    assert result.speech_text == "그 대까는 컸습니다."
    assert "<STANDARD_PRONUNCIATION_ENHANCEMENT>" in captured["prompt"]
    assert '"surface":"대가"' in captured["prompt"]
    assert '"options":["대까"]' in captured["prompt"]


def test_level5_validation_failure_falls_back_without_retry(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    monkeypatch.setattr(
        stage_engine,
        "generate",
        lambda **_kwargs: GenerationResult(text="궁무른 조씀니다.", elapsed_ms=2.0),
    )

    result = stage_engine.transform(
        "국물은 좋습니다.",
        model="gemma4:e4b",
        prompt_level=3,
    )

    assert result.speech_text == "국물은 좋습니다."
    assert result.validation_fallback is True
    assert result.rejected_speech_text == "궁무른 조씀니다."


def test_level5_validator_uses_the_exact_supplied_work_plan(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://llm.invalid/api")
    monkeypatch.setenv("LOCAL_LLM_TOKEN", "dummy-test-credential")
    monkeypatch.setattr(
        stage_engine,
        "generate",
        lambda **_kwargs: GenerationResult(text="그 대까는 컸습니다.", elapsed_ms=2.0),
    )

    result = stage_engine.transform(
        "그 대가는 컸습니다.",
        model="gemma4:e4b",
        prompt_level=3,
        stage5_work_plan=stage_engine.Stage5WorkPlan(),
    )

    assert result.speech_text == "그 대가는 컸습니다."
    assert result.validation_fallback is True
    assert result.validation_issues[0].code == "INVALID_SELECTION_RESPONSE"


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

    result = stage_engine.transform("KBS news 보도입니다.", model="gemma4:e4b")
    assert result.speech_text == "KBS news 보도입니다."
    assert result.validation_fallback is True


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

    result = stage_engine.transform("올해 상반기 매출이 늘었습니다.", model="gemma4:e4b")
    assert result.speech_text == "올해 상반기 매출이 늘었습니다."
    assert result.validation_fallback is True


def test_stage_engine_routes_vllm_model_to_vllm_client(monkeypatch) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    captured = {}

    def fake_generate_vllm(*, model, prompt, settings):
        captured["model"] = model
        captured["base_url"] = settings.base_url
        return GenerationResult(text='{"schema_version":1,"decisions":[]}', elapsed_ms=8.0)

    monkeypatch.setattr(stage_engine, "generate_vllm", fake_generate_vllm)

    result = stage_engine.transform(
        "국물은 좋습니다.",
        model="gemma4-31B-it (vLLM)",
    )

    assert result.speech_text == "국물은 좋습니다."
    assert result.model == "gemma4-31B-it (vLLM)"
    assert result.elapsed_ms == 8.0
    assert captured == {
        "model": "google/gemma-4-31B-it",
        "base_url": "http://vllm.invalid/v1",
    }


def test_stage_engine_runs_vllm_candidate_batches_concurrently(monkeypatch) -> None:
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
        assert source in prompt
        return GenerationResult(text='{"schema_version":1,"decisions":[]}', elapsed_ms=40.0)

    monkeypatch.setattr(stage_engine, "generate_vllm", fake_generate_vllm)

    source = "3번 맡았다.\n\n" * 100
    result = stage_engine.transform(
        source,
        model="gemma4-31B-it (vLLM)",
    )

    assert result.speech_text == source
    assert result.validation_fallback is False
    assert result.model == "gemma4-31B-it (vLLM)"
    assert captured["max_inflight"] == 2
    assert len(captured["prompts"]) == 2
    assert all(source in prompt for prompt in captured["prompts"])


def test_level5_vllm_uses_one_full_context_selection_request(
    monkeypatch,
) -> None:
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.invalid/v1")
    monkeypatch.setenv("VLLM_TOKEN", "dummy-vllm-test-token")
    captured = []
    source = "그 대가는 큽니다.\n\n노동의 대가는 작습니다."
    work_plan = build_stage5_work_plan(source)

    def fake_generate_vllm(*, model, prompt, settings):
        captured.append(prompt)
        return GenerationResult(
            text='{"schema_version":1,"decisions":[]}',
            elapsed_ms=1.0,
        )

    monkeypatch.setattr(stage_engine, "generate_vllm", fake_generate_vllm)
    result = stage_engine.transform(
        source,
        model="gemma4-31B-it (vLLM)",
        prompt_level=3,
        stage5_work_plan=work_plan,
    )

    assert result.speech_text == source
    assert len(captured) == 1
    prompt = captured[0]
    assert "그 대가는 큽니다.\n\n노동의 대가는 작습니다." in prompt
    assert prompt.count('"kind":"contextual_standard_pronunciation"') == 2


def test_stage_engine_runtime_asset_check_requires_no_llm_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LOCAL_LLM_TOKEN", raising=False)

    stage_engine.validate_runtime_assets()
