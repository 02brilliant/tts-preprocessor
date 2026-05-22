from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[10MB/s]", "10MB/s"),
        ("전송률은 [10MB/s]입니다", "전송률은 10MB/s입니다"),
        ("(10MB/s)", ""),
        ("전송률은 (10MB/s)입니다", "전송률은 입니다"),
        ("[60fps]", "60fps"),
        ("(60fps)", ""),
    ],
)
def test_phase17b_compound_inventory_bracket_protection(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
