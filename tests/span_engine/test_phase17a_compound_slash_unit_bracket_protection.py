from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[90km/h]", "90km/h"),
        ("속도는 [90km/h]입니다", "속도는 90km/h입니다"),
        ("(90km/h)", ""),
        ("속도는 (90km/h)입니다", "속도는 입니다"),
    ],
)
def test_compound_slash_unit_bracket_protection(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
