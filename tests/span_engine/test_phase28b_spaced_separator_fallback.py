from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12 .3", "12 .3"),
        ("12. 3", "12. 3"),
        ("12 · 3", "12 · 3"),
        ("12 · 3 수치", "12 · 3 수치"),
    ],
)
def test_spaced_separator_fallback_canonical(text: str, expected: str) -> None:
    # Phase 34A: spaced separators are preserved to avoid partial numeric rewrites.
    assert transform(text) == expected
