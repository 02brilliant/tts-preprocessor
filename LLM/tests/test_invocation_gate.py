from __future__ import annotations

import pytest

from LLM.invocation_gate import decide_llm_invocation
from LLM.stage5_preprocessor import preprocess_stage5


@pytest.mark.parametrize(
    "text",
    (
        "에이아이입니다.",
        "삼 킬로그램",
        "안녕하세요.",
        "오늘 맑습니다.",
        "사과 세 개.",
        "KBS news 조혜진입니다.",
        "report_v2.json입니다.",
        "This is a protected English sentence.",
        "색연필입니다.",
        "문고리를 잡았다.",
        "손등이 부었다.",
    ),
)
def test_level3_skips_short_rule_complete_or_intentionally_preserved_text(text: str) -> None:
    decision = decide_llm_invocation(text, stage_level=3)
    assert decision.call_llm is False
    assert decision.reason == "short_simple_rule_complete"


@pytest.mark.parametrize(
    ("text", "reason"),
    (
        ("새 장비 XQZ를 도입했습니다.", "actionable_residue"),
        (
            "오늘 정책을 검토했지만 추가 논의가 이어졌습니다.",
            "prosody_or_structure_candidate",
        ),
    ),
)
def test_level3_calls_for_actionable_or_uncertain_text(text: str, reason: str) -> None:
    decision = decide_llm_invocation(text, stage_level=3)
    assert decision.call_llm is True
    assert decision.reason == reason


def test_level4_skips_fewer_cases_than_level3() -> None:
    text = "사과 세 개."
    assert decide_llm_invocation(text, stage_level=3).call_llm is False
    decision = decide_llm_invocation(text, stage_level=4)
    assert decision.call_llm is True
    assert decision.reason == "natural_speech_candidate"


@pytest.mark.parametrize("text", ("안녕하세요.", "삼 킬로그램"))
def test_level4_skips_only_very_short_simple_text(text: str) -> None:
    decision = decide_llm_invocation(text, stage_level=4)
    assert decision.call_llm is False
    assert decision.reason == "stage4_rule_complete"


def test_level4_calls_for_natural_speech_contraction_candidate() -> None:
    decision = decide_llm_invocation("뉴스입니다.", stage_level=4)
    assert decision.call_llm is True
    assert decision.reason == "natural_speech_contraction_candidate"


def test_level5_rule_complete_pronunciation_skips_llm() -> None:
    prepared = preprocess_stage5("인기가 높습니다.")
    decision = decide_llm_invocation(
        prepared.text,
        stage_level=5,
        stage5_work_plan=prepared.work_plan,
    )
    assert prepared.text == "인끼가 높습니다."
    assert decision.call_llm is False
    assert decision.reason == "stage5_rule_complete"


def test_level5_skips_llm_for_clear_contextual_standard_pronunciation() -> None:
    prepared = preprocess_stage5("대가를 치렀다.")
    decision = decide_llm_invocation(
        prepared.text,
        stage_level=5,
        stage5_work_plan=prepared.work_plan,
    )
    assert prepared.text == "대까를 치렀다."
    assert decision.call_llm is False
    assert decision.reason == "stage5_rule_complete"


@pytest.mark.parametrize("text", ("색연필입니다.", "문고리를 잡았다.", "손등이 부었다."))
def test_fixed_pronunciation_is_not_an_llm_gate_reason(text: str) -> None:
    assert decide_llm_invocation(text, stage_level=3).call_llm is False
    decision = decide_llm_invocation(text, stage_level=4)
    assert decision.call_llm is False
    assert decision.reason == "stage4_rule_complete"


def test_long_compound_boundary_candidate_starts_at_level3() -> None:
    text = "산업용지역전기요금제입니다."
    for stage_level in (3, 4):
        decision = decide_llm_invocation(text, stage_level=stage_level)
        assert decision.call_llm is True
        assert decision.reason == "compound_boundary_candidate"

    prepared = preprocess_stage5(text)
    decision = decide_llm_invocation(
        prepared.text,
        stage_level=5,
        stage5_work_plan=prepared.work_plan,
    )
    assert decision.call_llm is True
    assert decision.reason == "compound_boundary_candidate"


def test_gate_rejects_stage5_plan_for_another_stage() -> None:
    plan = preprocess_stage5("대가입니다.").work_plan
    with pytest.raises(ValueError, match="only for stage 5"):
        decide_llm_invocation("대가입니다.", stage_level=4, stage5_work_plan=plan)


@pytest.mark.parametrize("stage_level", (False, 0, 2, 6))
def test_gate_rejects_invalid_stage_level(stage_level) -> None:
    with pytest.raises(ValueError):
        decide_llm_invocation("원고", stage_level=stage_level)
