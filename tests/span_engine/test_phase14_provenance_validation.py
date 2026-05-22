from __future__ import annotations

from engine.span_engine import SourceSpan, transform_with_trace


def test_event_keyword_stays_original_korean_for_validation() -> None:
    output = transform_with_trace("12.12 사태")

    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("십이십이", "GENERATED_READING", SourceSpan(0, 5), "event"),
        (" ", "ORIGINAL_SPACE", SourceSpan(5, 6), None),
        ("사태", "ORIGINAL_KOREAN", SourceSpan(6, 8), None),
    ]
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_emergency_context_and_tail_provenance() -> None:
    output = transform_with_trace("긴급번호 112는")

    assert output.normalized_text == "긴급번호 일일이는"
    assert ("긴급번호", "ORIGINAL_KOREAN") in [
        (piece.text, piece.provenance) for piece in output.render_pieces
    ]
    assert ("일일이", "GENERATED_READING", "emergency") in [
        (piece.text, piece.provenance, piece.owner) for piece in output.render_pieces
    ]
    assert any(
        piece.text == "는" and piece.provenance in {"ORIGINAL_KOREAN", "GENERATED_PARTICLE"}
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_one_digit_event_now_has_generated_reading() -> None:
    output = transform_with_trace("12.3 비상계엄")

    # Phase 28B: Expected to fail until Phase 28C
    assert output.normalized_text == "십이삼 비상계엄"
    assert any(
        piece.provenance == "GENERATED_READING" and piece.text == "십이삼"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
