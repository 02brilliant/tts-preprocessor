from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI", "에이아이"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("FTA은", "에프티에이는"),
        ("€50을 냈다", "오십 유로를 냈다"),
    ],
)
def test_phase2_regression_under_phase7_supported_owners(text: str, expected: str) -> None:
    assert transform(text) == expected
    assert transform_with_trace(text).normalized_text == expected


@pytest.mark.parametrize("value", [None, 123, b"bytes", ["text"]])
def test_phase2_type_guard_regression(value: object) -> None:
    with pytest.raises(TypeError):
        transform(value)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        transform_with_trace(value)  # type: ignore[arg-type]
