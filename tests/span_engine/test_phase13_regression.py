from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("50kg", "오십-킬로그램"),
        ("21명", "스물한-명"),
        ("3~8cm", "삼에서 팔-센티미터"),
        ("2025-01-03", "이천이십오년 일월 삼일"),
        ("회의는 13:05에 시작한다", "회의는 십삼시 오분에 시작한다"),
        ("13:05", "십삼시 오분"),
        ("OpenAI", "오픈 에이아이"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
    ],
)
def test_phase13_regression_cases(text: str, expected: str) -> None:
    assert transform(text) == expected
