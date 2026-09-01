from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("12·3 비상계엄", "십이삼 비상계엄"),
        ('12.3-비상계엄', '십이-쩜-삼-비상계엄'),
        ("12·3-비상계엄", "일이·삼-비상계엄"),
        ("6.27 부동산대책", "육이칠 부동산대책"),
        ("6·27 부동산대책", "육이칠 부동산대책"),
    ],
)
def test_event_numeric_blocks_compact_under_event_owner_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('12.3', '십이-쩜-삼'),
        ("12·3", "일이·삼"),
        ("12·3수치", "일이·삼수치"),
        ("12·3-수치", "일이·삼-수치"),
    ],
)
def test_non_event_decimal_and_middle_dot_fallback_spacing_remains(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
