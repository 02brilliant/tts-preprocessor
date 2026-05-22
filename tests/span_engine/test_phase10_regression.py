from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize("value", [None, 123, b"bytes", ["text"]])
def test_phase10_type_guard_regression(value: object) -> None:
    with pytest.raises(TypeError):
        transform(value)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        transform_with_trace(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("OpenAI", "OpenAI"),
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("123입니다", "백이십삼입니다"),
        ("[50kg]", "50kg"),
        ("(50kg)", ""),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("21명", "스물한 명"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
    ],
)
def test_phase10_regression_cases(text: str, expected: str) -> None:
    assert transform(text) == expected
