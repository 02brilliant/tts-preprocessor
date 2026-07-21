from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI", "에이아이"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("FTA은", "에프티에이는"),
        ("전문  가", "전문  가"),
        ("안녕하세요,", "안녕하세요,"),
    ],
)
def test_phase4_regression_under_phase7_supported_owners(text: str, expected: str) -> None:
    assert transform(text) == expected
    assert transform_with_trace(text).normalized_text == expected
