from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~11월", "일월에서 십일월"),
        ("3~5일", "삼일에서 오~일"),
        ("2020~2025년", "이~천이십년에서 이~천이십오년"),
        ("1~3층", "일에서 삼-층"),
        ("101~103호", "백일에서 백삼-호"),
        ("10~20원", "십에서 이~십-원"),
        ("20~30도", "이~십에서 삼십도"),
    ],
)
def test_shared_korean_suffix_range(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_shared_korean_suffix_is_original_korean_not_generated() -> None:
    output = transform_with_trace("1~11월입니다")

    assert output.normalized_text == "일월에서 십일월입니다"
    assert [
        (piece.text, piece.provenance, piece.source_span, piece.owner)
        for piece in output.render_pieces
    ] == [
        ("일월에서 십일", "GENERATED_READING", SourceSpan(0, 4), "range"),
        ("월입니다", "ORIGINAL_KOREAN", SourceSpan(4, 8), None),
    ]
