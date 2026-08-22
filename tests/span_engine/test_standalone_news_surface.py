from __future__ import annotations

import pytest

from engine.main import transform, transform_simplified
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("오늘 뉴스 보도입니다.", "오늘 뉴스 보도입니다."),
        (" 뉴스 ", "뉴스"),
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


def test_kbs_news_is_a_shared_phrase_dictionary_entry() -> None:
    output = transform_with_trace("KBS 뉴스")

    assert output.normalized_text == "KBS news"
    assert transform_simplified("KBS 뉴스") == "KBS news"
    assert output.trace is not None
    assert any(
        claim.owner == "phrase_dictionary"
        and claim.reason == "dictionary_fixed_phrase_match"
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.text == "KBS news"
        and piece.provenance == "GENERATED_READING"
        and piece.owner == "phrase_dictionary"
        for piece in output.render_pieces
    )
    assert all(log.passed for log in output.trace.validation_logs)


def test_simplified_disables_only_general_english_fallbacks() -> None:
    source = "ABC와 M&A, KOSPI, KBS-1, API2, 3kg"
    assert transform_simplified(source) == (
        "ABC와 M&A, 코스피, 케이비에스-원, 에이피아이 투, 삼 킬로그램"
    )
