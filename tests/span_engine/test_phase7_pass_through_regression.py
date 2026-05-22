from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize("value", [None, 123, b"bytes", ["text"]])
def test_phase7_type_guard_regression(value: object) -> None:
    with pytest.raises(TypeError):
        transform(value)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        transform_with_trace(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("㎏", "㎏"),
        ("㎡", "㎡"),
        ("１", "１"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
        ("{{S:사용자입력}}", "{{S:사용자입력}}"),
    ],
)
def test_phase7_no_normalization_or_tag_interpretation_regression(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
