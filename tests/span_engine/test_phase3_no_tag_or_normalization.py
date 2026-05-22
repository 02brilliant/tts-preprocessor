from __future__ import annotations

import pytest

from engine.span_engine import transform_with_trace
from engine.span_engine.render import join_render_pieces, render_tokens_pass_through
from engine.span_engine.tokenizer import tokenize_immutable_spans, validate_token_coverage


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("㎏", "㎏"),
        ("㎡", "㎡"),
        ("１", "１"),
        ("[[K:사용자입력]]", "[K:사용자입력]"),
        ("{{S:사용자입력}}", "{{S:사용자입력}}"),
    ],
)
def test_no_unicode_normalization_or_tag_interpretation(
    raw_text: str, expected: str
) -> None:
    tokens = tokenize_immutable_spans(raw_text)
    pieces = render_tokens_pass_through(tokens)
    output = transform_with_trace(raw_text)

    validate_token_coverage(raw_text, tokens)
    assert "".join(token.raw for token in tokens) == raw_text
    assert join_render_pieces(pieces) == raw_text
    assert output.normalized_text == expected
    assert "".join(piece.text for piece in output.render_pieces) == raw_text
