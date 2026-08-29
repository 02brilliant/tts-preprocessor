from __future__ import annotations

import pytest

from LLM.provenance import build_normalization_snapshot
from LLM.client import LLMResponseError
from LLM.pronunciation_overlay import apply_pronunciation_overlay
from LLM.response_validation import LLMStageContractError, validate_response
from engine.span_engine.transform import transform_with_trace


def test_level4_rejects_general_phonetic_rewrite() -> None:
    source = "국물은 같이 읽고 있습니다."
    output = "궁무른, 가치 일꼬 읻씀니다."

    with pytest.raises(LLMStageContractError, match="outside its whitelist"):
        validate_response(source, output, prompt_level=2)


@pytest.mark.parametrize(
    ("source", "output"),
    (
        ("색연필입니다.", "색년필입니다."),
        ("문고리를 잡았다.", "문꼬리를 잡았다."),
        ("손등이 부었다.", "손뜽이 부었다."),
        ("협력을 강화했다.", "혐녁을 강화했다."),
    ),
)
def test_level3_rejects_korean_pronunciation_spelling_changes(
    source: str,
    output: str,
) -> None:
    with pytest.raises(LLMStageContractError, match="outside its whitelist"):
        validate_response(source, output, prompt_level=1)


@pytest.mark.parametrize(
    ("source", "output"),
    (
        ("색연필입니다.", "색년필입니다."),
        ("문고리를 잡았다.", "문꼬리를 잡았다."),
        ("손등이 부었다.", "손뜽이 부었다."),
    ),
)
def test_level4_rejects_fixed_pronunciation_when_overlay_was_not_applied(
    source: str,
    output: str,
) -> None:
    with pytest.raises(LLMStageContractError, match="outside its whitelist"):
        validate_response(source, output, prompt_level=2)


def test_level3_allows_new_hangul_for_residual_english_reading() -> None:
    source = "AI는 좋습니다."
    output = "에이아이는 좋습니다."
    assert validate_response(source, output, prompt_level=1) == output


@pytest.mark.parametrize("prompt_level", (1, 2))
def test_every_llm_stage_accepts_closed_compound_boundary(
    prompt_level: int,
) -> None:
    source = "산업용지역전기요금제입니다."
    output = "산업용지역-전기요금제입니다."
    assert validate_response(source, output, prompt_level=prompt_level) == output


def test_level3_rejects_korean_rewrite_disguised_as_compound_boundary() -> None:
    with pytest.raises(LLMStageContractError, match="finite pronunciation entry"):
        validate_response(
            "산업용지역전기요금제입니다.",
            "산업용지역-전기요금재입니다.",
            prompt_level=1,
        )


def test_stage_outputs_form_a_controlled_processing_superset() -> None:
    source = "3.05와 색연필, 생산량을 확인했습니다."
    level3 = "삼쩜영오와 색연필, 생산량을 확인했습니다."
    level4_base = apply_pronunciation_overlay(level3, stage=4)
    level4 = level4_base.text

    assert validate_response(source, level3, prompt_level=1) == level3
    assert level4 == "삼쩜영오와 색년필, 생산냥을 확인했습니다."
    assert validate_response(level4, level4, prompt_level=2, snapshot=level4_base.snapshot) == level4

    with pytest.raises(LLMStageContractError):
        validate_response(source, level4, prompt_level=1)


@pytest.mark.parametrize(
    "output",
    (
        "궁무른 가치 일꼬 읻씀니다",
        "궁무른\n가치 일꼬 읻씀니다.",
        "궁무른; 가치 일꼬 읻씀니다.",
        "```궁무른 가치 일꼬 읻씀니다.```",
        "**궁무른 가치 일꼬 읻씀니다.**",
    ),
)
def test_integrated_response_rejects_structure_or_wrapper_changes(
    output: str,
) -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response("국물은 같이 읽고 있습니다.", output)

    assert exc_info.value.stage == "speech"
    assert exc_info.value.output_text == output
    assert isinstance(exc_info.value, LLMResponseError)


def test_level4_rejects_unapproved_rewrite_even_when_structure_is_preserved() -> None:
    source = "첫 문장,\n둘째 문장."
    output = "첟 문장, \n둘째 문장."

    with pytest.raises(LLMStageContractError, match="outside its whitelist"):
        validate_response(source, output)


def test_semantic_negation_mutation_is_critical() -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response("정부는 승인하지않았습니다.", "정부는 승인했습니다.")
    assert exc_info.value.code == "SEMANTIC_MUTATION"
    assert exc_info.value.severity == "Critical"


def test_integrated_response_accepts_insertions_before_existing_spaces() -> None:
    source = "첫 문장이고 둘째 문장이다."
    output = "첫 문장이고, 둘째 문장이다."

    assert validate_response(source, output) == output


@pytest.mark.parametrize(
    ("source", "output"),
    (
        (
            "오늘 아침 우리는 출발했습니다.",
            "오늘 아침, 우리는 출발했습니다.",
        ),
        (
            "올해 상반기 매출이 늘었습니다.",
            "올해 상반기, 매출이 늘었습니다.",
        ),
        (
            "올해 상반기 매출이 늘었습니다.",
            "올해, 상반기 매출이 늘었습니다.",
        ),
        (
            "내년 일분기 사업을 시작합니다.",
            "내년 일분기, 사업을 시작합니다.",
        ),
        (
            "내년 이월 삼일 서비스를 출시합니다.",
            "내년 이월 삼일, 서비스를 출시합니다.",
        ),
        (
            "내년 이월부터 사월까지 서비스를 시험합니다.",
            "내년 이월부터 사월까지, 서비스를 시험합니다.",
        ),
    ),
)
def test_integrated_response_rejects_new_stage1_time_frame_comma(
    source: str,
    output: str,
) -> None:
    with pytest.raises(LLMStageContractError, match="time-frame") as exc_info:
        validate_response(source, output)

    assert exc_info.value.output_text == output


def test_integrated_response_preserves_existing_stage1_time_frame_comma() -> None:
    source = "올해 상반기, 국내 주요 시장의 매출이 크게 늘었습니다."
    output = source

    assert validate_response(source, output) == output


def test_integrated_response_rejects_new_time_frame_comma_after_other_sentence() -> None:
    source = "첫 문장입니다. 내년 이월 서비스를 출시합니다."
    output = "첟 문장입니다. 내년 이월, 서비스를 출시합니다."

    with pytest.raises(LLMStageContractError, match="time-frame"):
        validate_response(source, output)


def test_integrated_response_preserves_stage1_confirmed_kbs_news_reading() -> None:
    with pytest.raises(LLMStageContractError, match="confirmed KBS news") as exc_info:
        validate_response("KBS news 보도입니다.", "KBS 뉴스 보도입니다.")

    assert exc_info.value.output_text == "KBS 뉴스 보도입니다."


def test_rule_generated_reading_mutation_is_critical_with_snapshot() -> None:
    output = transform_with_trace("55MW를 공급했습니다.")
    snapshot = build_normalization_snapshot(output)
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response(
            output.normalized_text,
            "오십육 메가와트를 공급했습니다.",
            prompt_level=1,
            snapshot=snapshot,
        )
    assert exc_info.value.code == "LOCKED_READING_MUTATION"
    assert exc_info.value.severity == "Critical"


@pytest.mark.parametrize("prompt_level", (1, 2))
def test_every_llm_stage_rejects_decimal_jjeom_rewrite(prompt_level: int) -> None:
    output = transform_with_trace("가격은 3.05달러입니다.")
    snapshot = build_normalization_snapshot(output)
    assert output.normalized_text == "가격은 삼쩜영오-달러입니다."

    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response(
            output.normalized_text,
            "가격은 삼점영오-달러입니다.",
            prompt_level=prompt_level,
            snapshot=snapshot,
        )

    assert exc_info.value.code == "LOCKED_READING_MUTATION"
    assert exc_info.value.severity == "Critical"


@pytest.mark.parametrize("prompt_level", (1, 2))
@pytest.mark.parametrize(
    ("source", "wrong_output"),
    (
        ("5kg을 운반했습니다.", "오 킬로그램을 운반했습니다."),
        ("1번째 항목입니다.", "첫 번째 항목입니다."),
        ("제7번째 항목입니다.", "제 일곱 번째 항목입니다."),
    ),
)
def test_every_llm_stage_rejects_locked_numeric_boundary_rewrite(
    prompt_level: int,
    source: str,
    wrong_output: str,
) -> None:
    output = transform_with_trace(source)
    snapshot = build_normalization_snapshot(output)

    assert "-" in output.normalized_text
    assert validate_response(
        output.normalized_text,
        output.normalized_text,
        prompt_level=prompt_level,
        snapshot=snapshot,
    ) == output.normalized_text

    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response(
            output.normalized_text,
            wrong_output,
            prompt_level=prompt_level,
            snapshot=snapshot,
        )

    assert exc_info.value.code == "LOCKED_READING_MUTATION"
    assert exc_info.value.severity == "Critical"


def test_unprocessed_speech_surface_is_medium() -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response("AI는 좋습니다.", "AI는 좋습니다.", prompt_level=1)
    assert exc_info.value.code == "RESIDUAL_SPEECH_SURFACE"
    assert exc_info.value.severity == "Medium"


def test_integrated_response_rejects_deleted_space_hidden_by_comma() -> None:
    with pytest.raises(LLMStageContractError):
        validate_response("첫 문장.", "첫,문장.")


@pytest.mark.parametrize(
    ("source", "output"),
    (
        ("2.35번 확인했다.", "이쩜삼오 번 확인했다."),
        ("1,000원을 냈다.", "천 원을 냈다."),
        ("09:30에 시작했다.", "아홉시 삼십분에 시작했다."),
    ),
)
def test_integrated_response_allows_consumed_numeric_separators(
    source: str,
    output: str,
) -> None:
    assert validate_response(source, output) == output


@pytest.mark.parametrize(
    ("source", "wrong_output"),
    (
        ("2.35번 확인했다.", "구쩜구구 번 확인했다."),
        ("1,000원을 냈다.", "이천 원을 냈다."),
        ("09:30에 시작했다.", "열시 삼십분에 시작했다."),
        ("55MW를 공급했다.", "오십육 메가와트를 공급했다."),
    ),
)
def test_integrated_response_rejects_numeric_meaning_mutation(
    source: str,
    wrong_output: str,
) -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response(source, wrong_output)
    assert exc_info.value.code == "NUMERIC_MEANING_MUTATION"
    assert exc_info.value.severity == "Critical"


def test_integrated_response_still_requires_filename_and_sentence_periods() -> None:
    with pytest.raises(LLMStageContractError):
        validate_response(
            "report_v2.json을 읽었다.",
            "report_v2json을 읽었다.",
        )


@pytest.mark.parametrize(
    ("source", "output"),
    (
        (
            "CPU 로그는 report_v2.json, https://example.com/3장, "
            "/tmp/3권/file에 있다.",
            "씨피유 로그는 report_v2.json, https://example.com/삼 장, "
            "/tmp/삼 권/file에 있다.",
        ),
        (
            '{"value":"3편"}와 `3층`은 코드 예시다.',
            '{"value":"삼 편"}와 `삼 층`은 코드 예시다.',
        ),
        (
            "제품 코드는 SKU-H100-25다.",
            "제품 코드는 에스케이유 에이치백 이십오다.",
        ),
    ),
)
def test_integrated_response_rejects_changed_protected_literals(
    source: str,
    output: str,
) -> None:
    with pytest.raises(LLMStageContractError, match="protected") as exc_info:
        validate_response(source, output)

    assert exc_info.value.output_text == output


def test_integrated_response_accepts_exact_protected_literals() -> None:
    source = (
        "CPU 로그는 report_v2.json, https://example.com/3장, "
        "/tmp/3권/file에 있다."
    )
    output = (
        "씨피유 로그는 report_v2.json, https://example.com/3장, "
        "/tmp/3권/file에 있다."
    )

    assert validate_response(source, output) == output
