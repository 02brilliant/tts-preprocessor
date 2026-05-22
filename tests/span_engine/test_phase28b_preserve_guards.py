from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[12.3]", "12.3"),
        ("[12·3]", "12·3"),
        ("A12.3B", "A12.3B"),
        ("A12·3B", "A12·3B"),
        ("2025-13-03", "이공이오 일삼 공삼"),
        ("2025-01-32", "이공이오 공일 삼이"),
        ("docs/2025/01/03", "docs/2025/01/03"),
        ("http://x/12.3", "http://x/12.3"),
        ("USB300", "USB300"),
    ],
)
def test_preserve_guards_canonical(text: str, expected: str) -> None:
    assert transform(text) == expected
