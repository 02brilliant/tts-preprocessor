from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[3만]", "3만"),
        ("수량은 [3만]입니다", "수량은 3만입니다"),
        ("(3만)", ""),
        ("수량은 (3만)입니다", "수량은 입니다"),
    ],
)
def test_large_unit_atomic_bracket_protection(text: str, expected: str) -> None:
    assert transform(text) == expected
