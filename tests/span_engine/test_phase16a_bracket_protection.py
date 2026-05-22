from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[-2℃]", "-2℃"),
        ("온도는 [-2℃]입니다", "온도는 -2℃입니다"),
        ("(-2℃)", ""),
        ("온도는 (-2℃)입니다", "온도는 입니다"),
        ("[+3°]", "+3°"),
        ("(+3°)", ""),
    ],
)
def test_signed_temperature_degree_bracket_protection(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
