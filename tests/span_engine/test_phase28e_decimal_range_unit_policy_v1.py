from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.5~8kg", "삼쩜오에서 팔 킬로그램"),
        ("3.5~8kg은", "삼쩜오에서 팔 킬로그램은"),
        ("3.5~8cm", "삼쩜오에서 팔 센티미터"),
        ("3.5~8cm의 폭", "삼쩜오에서 팔 센티미터의 폭"),
        ("0.5~1.2kg", "영쩜오에서 일쩜이 킬로그램"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("3~8kg", "삼에서 팔 킬로그램"),
    ],
)
def test_decimal_range_with_unit_full_consume_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "3.5~8kgabc",
        "3.5~8cmabc",
        "3.5~8unknown",
        "A3.5~8kgB",
    ],
)
def test_decimal_range_with_invalid_tail_preserves_policy_v1(text: str) -> None:
    assert transform(text) == text
