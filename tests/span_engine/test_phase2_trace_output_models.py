from __future__ import annotations

from engine.span_engine import (
    RenderPiece,
    SourceSpan,
    TransformOutput,
    TransformTrace,
    transform,
    transform_with_trace,
)


def test_transform_output_accepts_render_piece_sequence() -> None:
    piece = RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(2, 3))
    output = TransformOutput(normalized_text="abc", render_pieces=[piece])

    assert output.normalized_text == "abc"
    assert output.render_pieces == [piece]
    assert output.trace is None


def test_transform_trace_has_schema_log_lists_with_independent_defaults() -> None:
    trace1 = TransformTrace()
    trace2 = TransformTrace()

    trace1.claim_logs.append({"owner": "event"})

    assert trace2.claim_logs == []
    assert hasattr(trace1, "source_map_logs")
    assert hasattr(trace1, "tokenization_logs")
    assert hasattr(trace1, "shadow_logs")
    assert hasattr(trace1, "claim_logs")
    assert hasattr(trace1, "claim_collision_logs")
    assert hasattr(trace1, "gate_logs")
    assert hasattr(trace1, "parser_logs")
    assert hasattr(trace1, "fallback_logs")
    assert hasattr(trace1, "preserve_logs")
    assert hasattr(trace1, "particle_exception_logs")
    assert hasattr(trace1, "render_logs")
    assert hasattr(trace1, "validation_logs")
    assert hasattr(trace1, "prosody_logs")
    assert hasattr(trace1, "bracket_filter_logs")


def test_transform_with_trace_remains_pass_through_with_render_pieces() -> None:
    output = transform_with_trace("abc")

    assert output.normalized_text == "abc"
    assert "".join(piece.text for piece in output.render_pieces) == "abc"
    assert isinstance(output.trace, TransformTrace)


def test_phase1_pass_through_regression_cases() -> None:
    for text, expected in [
        ("AI", "에이아이"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("FTA은", "에프티에이는"),
    ]:
        assert transform(text) == expected
        assert transform_with_trace(text).normalized_text == expected
