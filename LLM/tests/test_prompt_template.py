from __future__ import annotations

from pathlib import Path

import pytest

from LLM.config import LLM_PROMPT_LV2_PATH, LLM_PROMPT_PATH
from LLM.prompt_template import PromptTemplateError, build_prompt


def test_prompt_replaces_exactly_one_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("앞\n{{NORMALIZED_TEXT}}\n뒤", encoding="utf-8")
    assert build_prompt("원고", path) == "앞\n원고\n뒤"


def test_prompt_reports_missing_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("자리표시자 없음", encoding="utf-8")
    with pytest.raises(PromptTemplateError, match="자리표시자가 없습니다"):
        build_prompt("원고", path)


def test_prompt_reports_duplicate_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("{{NORMALIZED_TEXT}}\n{{NORMALIZED_TEXT}}", encoding="utf-8")
    with pytest.raises(PromptTemplateError, match="자리표시자가 2개"):
        build_prompt("원고", path)


def test_prompt_reports_invalid_utf8(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff")
    with pytest.raises(PromptTemplateError, match="UTF-8"):
        build_prompt("원고", invalid)


def test_prompt_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PromptTemplateError, match="찾을 수 없습니다"):
        build_prompt("원고", tmp_path / "missing.txt")


def test_prompt_reloads_file_for_each_request(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("첫째 {{NORMALIZED_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "첫째 원고"
    path.write_text("둘째 {{NORMALIZED_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "둘째 원고"


def test_prompt_levels_have_distinct_closed_contracts() -> None:
    level3 = build_prompt("현장 원고", prompt_level=1)
    level4 = build_prompt("현장 원고", prompt_level=2)

    assert len({level3, level4}) == 2
    assert "3단계에서는 기존 한국어 철자를 발음형으로 바꾸지 않는다" in level3
    assert "색연필 → 색년필" not in level3
    assert "deterministic pronunciation overlay" in level4
    assert "색연필 → 색년필" not in level4
    for rendered in (level3, level4):
        assert "<NORMALIZED_TEXT>\n현장 원고\n</NORMALIZED_TEXT>" in rendered


def test_prompt_stage_inheritance_is_explicit_and_monotonic() -> None:
    level3 = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    level4 = LLM_PROMPT_LV2_PATH.read_text(encoding="utf-8")

    for prompt in (level3, level4):
        assert "<STAGE_INHERITANCE>" in prompt
        assert "<RESIDUAL_READING_NORMALIZATION>" in prompt

    assert "3단계에는 4단계의 한국어 발음 예외" in level3
    assert "4단계는 3단계의 통제된 상위 집합" in level4
    assert "overlay 이후 LLM이 추가하는 한국어 변경" in level4


def test_every_llm_prompt_requires_clear_residual_work_to_complete() -> None:
    for path in (LLM_PROMPT_PATH, LLM_PROMPT_LV2_PATH):
        prompt = path.read_text(encoding="utf-8")
        assert "2조 8천억 원 → 이조 팔천억 원" in prompt
        assert "한글 읽기" in prompt


@pytest.mark.parametrize("prompt_level", (0, 3, True))
def test_prompt_rejects_unknown_level(prompt_level) -> None:
    with pytest.raises(PromptTemplateError, match="prompt_level must be 1 or 2"):
        build_prompt("원고", prompt_level=prompt_level)


@pytest.mark.parametrize(
    "path",
    (LLM_PROMPT_PATH, LLM_PROMPT_LV2_PATH),
)
def test_every_active_prompt_has_one_plain_input_contract(path: Path) -> None:
    prompt = path.read_text(encoding="utf-8")
    assert prompt.count("{{NORMALIZED_TEXT}}") == 1
    assert "<OUTPUT_CONTRACT>" in prompt
    assert "<FINAL_VALIDATION>" in prompt
    assert "<PROTECTED_SURFACES>" in prompt
    assert "<RULE_ENGINE_LOCKED_RESULTS>" in prompt


def test_level3_prompt_preserves_korean_and_locked_readings() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    for fixed_reading in ("삼번 버스", "오분 뒤", "제 삼장", "KBS news"):
        assert fixed_reading in prompt
    assert "승인된 복합명사 ASCII 하이픈과 쉼표 외" in prompt
    assert "한국어 단어를 발음식으로 전사하지 않는다" in prompt


def test_compound_boundary_policy_is_inherited_from_level3() -> None:
    level3 = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    level4 = LLM_PROMPT_LV2_PATH.read_text(encoding="utf-8")

    assert "<COMPOUND_SPEECH_BOUNDARY>" in level3
    assert "한글 글자와 순서는 그대로 유지한다" in level3
    assert "3단계에서 상속한 운율 정책" in level4


def test_active_prompt_has_contextual_number_unit_handoff_contract() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    assert "규칙 엔진이 문맥 모호성 때문에 보류한" in prompt
    assert "3번 확인했다 → 세 번 확인했다" in prompt
    assert "3번 버스 → 삼번 버스" in prompt
    assert "0.5%p → 영쩜오 퍼센트포인트" in prompt
    assert "해석이 둘 이상이면 원형을 유지한다" in prompt


def test_active_prompt_locks_rule_canonical_readings_and_spacing() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    for fixed_reading in ("세 대", "삼번 버스", "오분 뒤", "제 삼장"):
        assert fixed_reading in prompt
    assert "띄어쓰기" in prompt
    assert "다시 판단하지 않는다" in prompt


def test_active_prompt_preserves_confirmed_kbs_news_phrase_without_tokens() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    assert "KBS news" in prompt
    assert "<LOCK_0001>" not in prompt


def test_active_prompt_locks_stage1_time_frame_comma_decisions() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    assert "문장 시작 시간구 뒤에 쉼표를 넣지 않은 결정도 유지한다" in prompt
    assert "문장 시작 시간구 뒤에 규칙 엔진이 쉼표를 두지 않은 위치" in prompt


def test_active_prompt_distinguishes_input_quotes_from_output_wrappers() -> None:
    prompt = LLM_PROMPT_PATH.read_text(encoding="utf-8")
    assert "기존 마침표·물음표·느낌표·괄호·따옴표" in prompt
    assert "설명, 분석, JSON, Markdown, 코드 블록, 머리말을 출력하지 않는다" in prompt


def test_level4_prompt_is_closed_and_rejects_general_g2p() -> None:
    prompt = LLM_PROMPT_LV2_PATH.read_text(encoding="utf-8")
    assert "<NATURAL_SPEECH_CONTRACTION>" in prompt
    assert "<DETERMINISTIC_PRONUNCIATION_OVERLAY>" in prompt
    assert "발음 목록을 추측·확장하지 않는다" in prompt
    assert "국물→궁물" in prompt
    assert "출력 철자에 반영하지 않는다" in prompt
    assert "복합 조사, 연속 어미" in prompt


@pytest.mark.parametrize("path", (LLM_PROMPT_LV2_PATH,))
def test_fixed_pronunciation_registry_is_not_duplicated_in_prompt(path: Path) -> None:
    prompt = path.read_text(encoding="utf-8")
    assert "색연필 → 색년필" not in prompt
    assert "생산량 → 생산냥" not in prompt
    assert "exact whole-word pronunciation overlay" in prompt


def test_active_prompt_injects_only_plain_normalized_text() -> None:
    normalized_text = "3번 확인했고 5분이 남았다."
    rendered = build_prompt(normalized_text)
    assert f"<NORMALIZED_TEXT>\n{normalized_text}\n</NORMALIZED_TEXT>" in rendered
    assert "<CONTEXTUAL_DECISION_LOGS>" not in rendered
    assert "<DECISION_CANDIDATES>" not in rendered


@pytest.mark.parametrize(
    "path",
    (LLM_PROMPT_PATH, LLM_PROMPT_LV2_PATH),
)
def test_decimal_examples_match_the_rule_engine_locked_jjeom_surface(path: Path) -> None:
    prompt = path.read_text(encoding="utf-8")
    assert "삼쩜영오" in prompt
    assert "영쩜오 퍼센트포인트" in prompt
    assert "삼 점 영오" not in prompt
    assert "영 점 오 퍼센트포인트" not in prompt


@pytest.mark.parametrize(
    "path",
    (LLM_PROMPT_PATH, LLM_PROMPT_LV2_PATH),
)
def test_large_residual_currency_reading_example_is_in_every_prompt(path: Path) -> None:
    assert "2조 8천억 원 → 이조 팔천억 원" in path.read_text(encoding="utf-8")
