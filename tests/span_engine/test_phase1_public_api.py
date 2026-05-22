from __future__ import annotations

from dataclasses import fields, is_dataclass

import pytest

from engine.span_engine import TransformTrace, transform, transform_with_trace
from engine.span_engine.models import TransformOutput


def test_public_api_imports_and_returns_pass_through_text() -> None:
    assert transform("abc") == "abc"


def test_transform_with_trace_returns_minimal_transform_output() -> None:
    output = transform_with_trace("abc")

    assert isinstance(output, TransformOutput)
    assert output.normalized_text == "abc"
    assert "".join(piece.text for piece in output.render_pieces) == "abc"
    assert isinstance(output.trace, TransformTrace)


def test_transform_output_minimal_field_contract() -> None:
    assert is_dataclass(TransformOutput)
    assert [field.name for field in fields(TransformOutput)] == [
        "normalized_text",
        "render_pieces",
        "trace",
    ]


@pytest.mark.parametrize("value", [None, 123, b"bytes", ["text"]])
def test_transform_rejects_non_str_input(value: object) -> None:
    with pytest.raises(TypeError):
        transform(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [None, 123, b"bytes", ["text"]])
def test_transform_with_trace_rejects_non_str_input(value: object) -> None:
    with pytest.raises(TypeError):
        transform_with_trace(value)  # type: ignore[arg-type]
