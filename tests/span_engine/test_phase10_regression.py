from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("OpenAI", "오픈 에이아이"),
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("123입니다", "백이십삼입니다"),
        ("[50kg]", "50kg"),
        ("(50kg)", ""),
        ("3~8cm", "삼에서 팔-센티미터"),
        ("21명", "스물한-명"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
    ],
)
def test_phase10_regression_cases(text: str, expected: str) -> None:
    assert transform(text) == expected
