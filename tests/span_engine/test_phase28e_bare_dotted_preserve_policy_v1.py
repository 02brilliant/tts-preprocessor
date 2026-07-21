from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025.01", "이천이십오쩜영일"),
        ("12.12", "십이쩜일이"),
        ("12.12가 있었다", "12.12가 있었다"),
        ("오늘 12.12가 있었다", "오늘 12.12가 있었다"),
        ("12.12(사태)", "십이쩜일이"),
        ("[12.12]", "12.12"),
        ("[12.12 사태]", "12.12 사태"),
    ],
)
def test_bare_dotted_two_block_routing_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
