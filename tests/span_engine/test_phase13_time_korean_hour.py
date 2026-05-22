from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시", "세 시"),
        ("3시에 시작", "세 시에 시작"),
        ("3시 5분", "세 시 오분"),
        ("3시 5분 7초", "세 시 오분 칠초"),
        ("오후 3시", "오후 세 시"),
        ("오전 10시 30분", "오전 열 시 삼십분"),
    ],
)
def test_korean_hour_time(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["3시리즈", "A3시", "3시abc", "99시", "3시 99분", "3시 5분 99초"],
)
def test_invalid_or_attached_korean_time_preserve(text: str) -> None:
    assert transform(text) == text


def test_korean_time_markers_remain_original_korean() -> None:
    output = transform_with_trace("3시 5분")

    assert output.normalized_text == "세 시 오분"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("세 ", "GENERATED_READING", SourceSpan(0, 1), "time"),
        ("시", "ORIGINAL_KOREAN", SourceSpan(1, 2), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(2, 3), None),
        ("오", "GENERATED_READING", SourceSpan(3, 4), "time"),
        ("분", "ORIGINAL_KOREAN", SourceSpan(4, 5), None),
    ]
