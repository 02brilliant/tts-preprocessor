from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12 .3", "12 .3"),
        ("12. 3", "12. 3"),
        ("12 · 3", "십이 · 삼"),
        ("12 · 3 수치", "십이 · 삼 수치"),
    ],
)
def test_spaced_separator_fallback_canonical(text: str, expected: str) -> None:
    # Period forms preserve; middle-dot forms keep the boundary and read both sides.
    assert transform(text) == expected
