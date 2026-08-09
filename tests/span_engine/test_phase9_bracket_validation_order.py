from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("회의는 13:05(시작)에 열린다", "회의는 십삼시 오분에 열린다"),
        ("값은 12.3(사태)이다", "값은 십이쩜삼이다"),
    ],
)
def test_parenthesis_content_does_not_leak_as_context(text: str, expected: str) -> None:
    output = transform_with_trace(text)

    # Phase 28B: Expected to fail until Phase 28C
    assert output.normalized_text == expected
    assert not any(claim.owner == "event" for claim in output.trace.claim_logs)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI(임시)은 중요하다", "임시는 중요하다"),
        ("AI은(임시) 중요하다", "에이아이는 중요하다"),
    ],
)
def test_safe_particle_exception_runs_before_final_bracket_filter(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_validation_runs_before_final_bracket_filter() -> None:
    parenthesis = transform_with_trace("문장(임시)입니다")
    square = transform_with_trace("가격은 [3kg]입니다")

    assert parenthesis.normalized_text == "문장입니다"
    assert square.normalized_text == "가격은 3kg입니다"
    assert all(log.passed for log in parenthesis.trace.validation_logs)
    assert all(log.passed for log in square.trace.validation_logs)
    assert any(log.event == "parenthesis_elided" for log in parenthesis.trace.bracket_filter_logs)
    assert any(log.event == "square_bracket_unwrapped" for log in square.trace.bracket_filter_logs)
