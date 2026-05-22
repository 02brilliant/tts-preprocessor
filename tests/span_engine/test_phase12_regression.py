from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize("value", [None, 123, b"bytes", ["text"]])
def test_phase12_type_guard_regression(value: object) -> None:
    with pytest.raises(TypeError):
        transform(value)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        transform_with_trace(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("50kg", "오십 킬로그램"),
        ("21명", "스물한 명"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("1~11월", "일월에서 십일월"),
        ("2025-01-03", "이천이십오년 일월 삼일"),
        ("123-456-7890", "일이삼 사오육 칠팔구공"),
        ("OpenAI", "OpenAI"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
    ],
)
def test_phase12_regression_cases(text: str, expected: str) -> None:
    assert transform(text) == expected
