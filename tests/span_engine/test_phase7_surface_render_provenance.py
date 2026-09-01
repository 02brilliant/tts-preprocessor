from __future__ import annotations

from engine.span_engine import SourceSpan, transform_with_trace


def test_dictionary_surface_render_separates_generated_reading_and_original_korean() -> None:
    output = transform_with_trace("GPT는")

    assert [(piece.text, piece.provenance, piece.source_span, piece.owner) for piece in output.render_pieces] == [
        ("지피티", "GENERATED_READING", SourceSpan(0, 3), "dictionary"),
        ("는", "GENERATED_PARTICLE", SourceSpan(3, 4), "dictionary"),
    ]


def test_number_surface_render_separates_generated_reading_and_original_korean() -> None:
    output = transform_with_trace("123입니다")

    assert [(piece.text, piece.provenance, piece.source_span, piece.owner) for piece in output.render_pieces] == [
        ("백이십삼", "GENERATED_READING", SourceSpan(0, 3), "number"),
        ("입니다", "ORIGINAL_KOREAN", SourceSpan(3, 6), None),
    ]


def test_decimal_now_has_generated_reading() -> None:
    output = transform_with_trace("3.14")

    # Phase 28B: Expected to fail if implementation is not yet updated,
    # but it seems engine already normalizes 3.14 as decimal.
    assert output.normalized_text == "삼-쩜-일사"
    assert any(piece.provenance == "GENERATED_READING" for piece in output.render_pieces)
