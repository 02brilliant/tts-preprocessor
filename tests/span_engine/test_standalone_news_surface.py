from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("오늘 뉴스 보도입니다.", "오늘 news 보도입니다."),
        (" 뉴스 ", " news "),
    ],
)
def test_space_delimited_news_is_rendered_as_english(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "뉴스 보도입니다.",
        "오늘 뉴스",
        "오늘 뉴스입니다.",
        "에스토니아 수도 빌뉴스 입니다.",
        "뉴스타 부동산",
    ],
)
def test_news_without_both_whitespace_boundaries_is_preserved(source: str) -> None:
    assert transform(source) == source


def test_standalone_news_has_narrow_claim_and_shadow_exception() -> None:
    output = transform_with_trace("오늘 뉴스 보도입니다.")

    assert output.normalized_text == "오늘 news 보도입니다."
    assert output.trace is not None
    assert any(
        claim.owner == "standalone_news"
        and claim.reason == "space_delimited_news_to_english_reading"
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.text == "news"
        and piece.provenance == "GENERATED_READING"
        and piece.owner == "standalone_news"
        for piece in output.render_pieces
    )
    assert all(log.passed for log in output.trace.validation_logs)
