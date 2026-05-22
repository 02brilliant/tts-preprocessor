from __future__ import annotations

from engine.span_engine import SourceSpan, transform_with_trace


def test_counter_render_keeps_counter_noun_original_korean() -> None:
    output = transform_with_trace("21명")

    assert output.normalized_text == "스물한 명"
    assert [(piece.text, piece.provenance, piece.source_span, piece.owner) for piece in output.render_pieces] == [
        ("스물한 ", "GENERATED_READING", SourceSpan(0, 2), "counter_noun"),
        ("명", "ORIGINAL_KOREAN", SourceSpan(2, 3), None),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_counter_remainder_in_same_korean_token_is_preserved() -> None:
    output = transform_with_trace("참석자는 21명입니다")

    assert output.normalized_text == "참석자는 스물한 명입니다"
    assert any(piece.text == "명입니다" and piece.provenance == "ORIGINAL_KOREAN" for piece in output.render_pieces)
    assert all(log.passed for log in output.trace.validation_logs)
