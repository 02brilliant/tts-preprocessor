from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2025-01-03", "이천이십오년 일월 삼일"),
        ("2025/01/03", "이천이십오년 일월 삼일"),
        ("날짜는 2025-01-03입니다", "날짜는 이천이십오년 일월 삼일입니다"),
        ("날짜는 2025/01/03입니다", "날짜는 이천이십오년 일월 삼일입니다"),
        ("2025년 1월 3일", "이천이십오년 일월 삼일"),
        ("행사는 1월 3일입니다", "행사는 일월 삼일입니다"),
        ("2025년 1월", "이천이십오년 일월"),
        ("올해는 2025년입니다", "올해는 이천이십오년입니다"),
    ],
)
def test_date_basic(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_korean_date_markers_remain_original_korean() -> None:
    output = transform_with_trace("2025년 1월 3일")

    assert output.normalized_text == "이천이십오년 일월 삼일"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("이천이십오", "GENERATED_READING", SourceSpan(0, 4), "date"),
        ("년", "ORIGINAL_KOREAN", SourceSpan(4, 5), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(5, 6), None),
        ("일", "GENERATED_READING", SourceSpan(6, 7), "date"),
        ("월", "ORIGINAL_KOREAN", SourceSpan(7, 8), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(8, 9), None),
        ("삼", "GENERATED_READING", SourceSpan(9, 10), "date"),
        ("일", "ORIGINAL_KOREAN", SourceSpan(10, 11), None),
    ]
