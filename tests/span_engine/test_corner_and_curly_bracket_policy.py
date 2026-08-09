from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("문장 【AI 3kg】 확인", "문장 【AI 3kg】 확인"),
        ("문장 {AI 3kg} 확인", "문장 AI 3kg 확인"),
        ('문장 {"price":"KRW1000"} 확인', '문장 {"price":"KRW1000"} 확인'),
        ("문장 {key: value} 확인", "문장 {key: value} 확인"),
        ("문장 (AI 3kg) 확인", "문장 확인"),
        ("【문장(임시)】", "【문장(임시)】"),
        ("{문장(임시)}", "문장(임시)"),
        ("(문장{임시})", ""),
    ],
)
def test_corner_curly_and_parenthesis_presentation_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_corner_and_curly_bracket_interiors_are_protected_before_claim() -> None:
    output = transform_with_trace("【AI 3kg】 {AI 3kg} JSON")

    assert output.normalized_text == "【AI 3kg】 AI 3kg 제이슨"
    assert not any(
        claim.owner in {"dictionary", "simple_unit", "number"}
        and claim.span.start < 18
        for claim in output.trace.claim_logs
    )
    assert any(claim.owner == "dictionary" and claim.span.start >= 18 for claim in output.trace.claim_logs)
    assert {log.event for log in output.trace.bracket_filter_logs} >= {
        "corner_bracket_preserved",
        "curly_brace_unwrapped",
    }


def test_json_like_curly_braces_remain_protected_literals() -> None:
    output = transform_with_trace('{"price":"KRW1000"} 밖의 KRW1000')

    assert output.normalized_text == '{"price":"KRW1000"} 밖의 천 원'
    assert any(claim.owner == "preserve" for claim in output.trace.claim_logs)
    assert not any(log.event == "curly_brace_unwrapped" for log in output.trace.bracket_filter_logs)


@pytest.mark.parametrize(
    "text",
    ["【AI", "AI】", "{AI", "AI}"],
)
def test_incomplete_corner_and_curly_brackets_are_preserved(text: str) -> None:
    assert transform(text) == text
