from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, SpanToken
from engine.span_engine.render import (
    join_render_pieces,
    render_token,
    render_tokens_pass_through,
)
from engine.span_engine.tokenizer import tokenize_immutable_spans


@pytest.mark.parametrize(
    "raw_text",
    [
        "전문  가,",
        "AI는 123입니다",
        "[[K:사용자입력]]",
    ],
)
def test_render_tokens_pass_through_joins_to_original_text(raw_text: str) -> None:
    tokens = tokenize_immutable_spans(raw_text)
    pieces = render_tokens_pass_through(tokens)

    assert join_render_pieces(pieces) == raw_text
    for token, piece in zip(tokens, pieces, strict=True):
        assert piece.text == token.raw
        assert piece.source_span == token.span


def test_render_token_maps_token_kind_to_original_provenance() -> None:
    cases = [
        (SpanToken("KOREAN_LITERAL", "가", SourceSpan(0, 1)), "ORIGINAL_KOREAN"),
        (SpanToken("SPACE_LOCK", " ", SourceSpan(1, 2)), "ORIGINAL_SPACE"),
        (SpanToken("PUNCT_LOCK", ",", SourceSpan(2, 3)), "ORIGINAL_PUNCT"),
        (SpanToken("BOUNDARY_LITERAL", "[", SourceSpan(0, 1)), "ORIGINAL_BOUNDARY"),
        (SpanToken("PLAIN", "AI", SourceSpan(0, 2)), "ORIGINAL_BOUNDARY"),
    ]

    for token, provenance in cases:
        assert render_token(token).provenance == provenance


def test_render_token_preserves_surface_token_raw_in_phase3() -> None:
    token = SpanToken("SURFACE", "AI", SourceSpan(0, 2), owner="dictionary")
    piece = render_token(token)

    assert piece.text == "AI"
    assert piece.provenance == "ORIGINAL_BOUNDARY"
    assert piece.source_span == SourceSpan(0, 2)
