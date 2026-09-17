from __future__ import annotations

import pytest

from engine.main import transform, transform_output, transform_simplified
from LLM.provenance import build_normalization_snapshot
from LLM.response_validation import LLMStageContractError, validate_response
from LLM.stage3_preprocessor import preprocess_stage3
from LLM.stage4_preprocessor import preprocess_stage4


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("[AI 3kg 국물입니다.]", "[AI 3kg 국물입니다.]"),
        ("{AI 3kg 국물입니다.}", "AI 3kg 국물입니다."),
        ("(AI 3kg 국물입니다.)", ""),
        ("[  가 나  ]", "[  가 나  ]"),
        ("{  가 나  }", "  가 나  "),
        ('{"price":"KRW1000"}', '"price":"KRW1000"'),
        ("{key: value}", "key: value"),
        ("{AI 3kg}", "AI 3kg"),
        ("[가{나}(다)]", "[가{나}(다)]"),
        ("{가[나](다)}", "가[나](다)"),
        ("(가[나]{다})", ""),
        ("[국물입니다.] {학교입니다.} (삭제)", "[국물입니다.] 학교입니다."),
        ("{}[]()", "[]"),
    ],
)
def test_bracket_policy_is_shared_by_all_four_stages(source, expected):
    assert transform_simplified(source) == expected  # stage 1
    assert transform(source) == expected  # stage 2
    output = transform_output(source)
    snapshot = build_normalization_snapshot(output)
    for preprocess in (preprocess_stage3, preprocess_stage4):
        prepared = preprocess(output.normalized_text, snapshot=snapshot)
        assert prepared.text == expected
        assert prepared.work_plan.candidates == ()


@pytest.mark.parametrize("prompt_level", [1, 3])
@pytest.mark.parametrize("source", ["[AI]", "{AI}"])
def test_llm_cannot_rewrite_protected_bracket_content(source, prompt_level):
    output = transform_output(source)
    snapshot = build_normalization_snapshot(output)
    with pytest.raises(LLMStageContractError):
        validate_response(
            output.normalized_text,
            output.normalized_text.replace("AI", "에이아이"),
            prompt_level=prompt_level,
            snapshot=snapshot,
        )


def test_protected_offsets_survive_deleted_parentheses_and_repeated_text():
    output = transform_output("(국물입니다.) {국물입니다.} [국물입니다.]")
    snapshot = build_normalization_snapshot(output)
    assert [span.text for span in snapshot.spans if span.protected] == [
        "국물입니다.", "[국물입니다.]",
    ]
    assert preprocess_stage4(output.normalized_text, snapshot=snapshot).text == output.normalized_text


def test_brackets_do_not_disable_neighboring_pronunciation_processing():
    output = transform_output("{국물입니다.} 국물입니다.")
    prepared = preprocess_stage4(
        output.normalized_text, snapshot=build_normalization_snapshot(output)
    )
    assert prepared.text.startswith("국물입니다. ")
    assert prepared.text != output.normalized_text


def test_parenthetical_hangul_alias_is_retained_in_all_stages():
    source = "AI(인공지능) 플랫폼"
    assert transform_simplified(source) == "인공지능 플랫폼"
    output = transform_output(source)
    assert output.normalized_text == "인공지능 플랫폼"
    snapshot = build_normalization_snapshot(output)
    for preprocess in (preprocess_stage3, preprocess_stage4):
        assert preprocess(output.normalized_text, snapshot=snapshot).text == "인공지능 플랫폼"


@pytest.mark.parametrize("opening,closing", [("[", "]"), ("{", "}"), ("(", ")")])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r", "\n\n"])
def test_multiline_brackets_ignore_presentation_policy_in_all_stages(opening, closing, newline):
    source = f"{opening}가{newline}나{closing}"
    separator = ", " if newline == "\n\n" else " "
    expected = f"{opening}가{separator}나{closing}"
    assert transform_simplified(source) == expected
    output = transform_output(source)
    assert output.normalized_text == expected
    assert output.protected_spans == []
    assert output.trace.bracket_filter_logs == []
    snapshot = build_normalization_snapshot(output)
    for preprocess in (preprocess_stage3, preprocess_stage4):
        assert preprocess(output.normalized_text, snapshot=snapshot).text == expected


def test_multiline_brackets_do_not_lock_content_against_correction():
    output = transform_output("[국물\n입니다.]")
    snapshot = build_normalization_snapshot(output)
    assert not any(span.protected for span in snapshot.spans)
    assert preprocess_stage4(output.normalized_text, snapshot=snapshot).text == "[궁물 입니다.]"


def test_multiline_exception_is_local_to_its_bracket_range():
    output = transform_output("{가\n나} {AI 3kg} (삭제) [AI 3kg]")
    assert output.normalized_text == "{가 나} AI 3kg [AI 3kg]"
    assert [output.normalized_text[span.start:span.end] for span in output.protected_spans] == [
        "AI 3kg", "[AI 3kg]",
    ]


def test_multiline_outer_bracket_does_not_elide_nested_parentheses():
    output = transform_output("[가(나)\n다]")
    assert output.normalized_text == "[가(나) 다]"
    assert output.trace.bracket_filter_logs == []
