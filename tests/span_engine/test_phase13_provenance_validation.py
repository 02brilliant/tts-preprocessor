from __future__ import annotations

from engine.span_engine import SourceSpan, transform_with_trace


def test_separator_date_provenance_and_validation() -> None:
    output = transform_with_trace("날짜는 2025-01-03입니다")

    assert output.normalized_text == "날짜는 이천이십오년 일월 삼일입니다"
    assert ("날짜는", "ORIGINAL_KOREAN") in [
        (piece.text, piece.provenance) for piece in output.render_pieces
    ]
    assert (
        "이천이십오년 일월 삼일",
        "GENERATED_READING",
        SourceSpan(4, 14),
        "date",
    ) in [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ]
    assert ("입니다", "ORIGINAL_KOREAN") in [
        (piece.text, piece.provenance) for piece in output.render_pieces
    ]
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_colon_time_provenance_and_validation() -> None:
    output = transform_with_trace("회의는 13:05에 시작한다")

    assert output.normalized_text == "회의는 십삼시 오분에 시작한다"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("회의는", "ORIGINAL_KOREAN", SourceSpan(0, 3), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(3, 4), None),
        ("십삼시 오분", "GENERATED_READING", SourceSpan(4, 9), "time"),
        ("에", "ORIGINAL_KOREAN", SourceSpan(9, 10), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(10, 11), None),
        ("시작한다", "ORIGINAL_KOREAN", SourceSpan(11, 15), None),
    ]
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
