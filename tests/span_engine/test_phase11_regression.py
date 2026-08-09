from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI은 중요하다", "에이아이는 중요하다"),
        ("50kg", "오십 킬로그램"),
        ("[21명]", "21명"),
        ("참석자는 [21명]입니다", "참석자는 21명입니다"),
        ("(21명)", ""),
        ("참석자는 (21명)입니다", "참석자는 입니다"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("OpenAI", "오픈 에이아이"),
    ],
)
def test_phase11_regression_cases(text: str, expected: str) -> None:
    assert transform(text) == expected
