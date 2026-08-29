from __future__ import annotations

from engine.span_engine import SourceSpan, transform_with_trace


def test_range_with_unit_render_piece_provenance() -> None:
    output = transform_with_trace("3~8cm")

    assert output.normalized_text == "삼에서 팔-센티미터"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("삼에서 팔-센티미터", "GENERATED_READING", SourceSpan(0, 5), "range_with_unit")
    ]


def test_sentence_range_preserves_surrounding_korean_literals() -> None:
    output = transform_with_trace("길이는 3~8cm입니다")

    assert output.normalized_text == "길이는 삼에서 팔-센티미터입니다"
    assert ("길이는", "ORIGINAL_KOREAN") in [
        (piece.text, piece.provenance) for piece in output.render_pieces
    ]
    assert ("입니다", "ORIGINAL_KOREAN") in [
        (piece.text, piece.provenance) for piece in output.render_pieces
    ]


def test_korean_suffix_range_keeps_suffix_original() -> None:
    output = transform_with_trace("1~3층")

    assert output.normalized_text == "일에서 삼-층"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("일에서 삼-", "GENERATED_READING", SourceSpan(0, 3), "range"),
        ("층", "ORIGINAL_KOREAN", SourceSpan(3, 4), None),
    ]
