from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("비용은 (약) 3만원입니다", "비용은 삼만 원입니다"),
        ("문장(임시)입니다", "문장입니다"),
        ("AI(테스트)는 중요하다", "에이아이는 중요하다"),
        ("값은 123(임시)입니다", "값은 백이십삼입니다"),
        ("문장(임시[확인])입니다", "문장입니다"),
        ("문장 (AI) 확인", "문장 확인"),
        ("문장 (123) 확인", "문장 확인"),
    ],
)
def test_parenthesis_content_is_elided_after_validation(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert transform(text) == expected
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(log.event == "parenthesis_elided" for log in output.trace.bracket_filter_logs)


def test_parenthesis_inner_surfaces_are_not_claimed() -> None:
    output = transform_with_trace("문장 (AI) 123 확인")

    assert output.normalized_text == "문장 백이십삼 확인"
    assert not any(
        claim.owner == "dictionary" and claim.span.start >= 4 and claim.span.end <= 8
        for claim in output.trace.claim_logs
    )
    assert any(claim.owner == "number" for claim in output.trace.claim_logs)
