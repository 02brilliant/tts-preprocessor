from __future__ import annotations

import pytest

from engine.main import transform_with_rollout
from engine.span_engine import transform_with_trace
from engine.span_engine.lexicon import DICTIONARY_READINGS


def production_transform(text: str) -> str:
    return transform_with_rollout(text, mode="span_default", include_debug=False)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("NASDAQ 지수", "나스닥 지수"),
        ("S&P 지수", "에스앤피 지수"),
        ("S&P500 지수", "에스앤피 오백 지수"),
        ("S&P 500 지수", "에스앤피 오백 지수"),
        (
            "미국 NASDAQ 지수와 S&P500 지수는 오늘 사상 최고가를 경신했다.",
            "미국 나스닥 지수와 에스앤피 오백 지수는 오늘 사상 최고가를 경신했다.",
        ),
        ("NASDAQ100 지수", "나스닥 백 지수"),
        ("NASDAQ 100 지수", "나스닥 백 지수"),
        ("KOSPI200 지수", "코스피 이백 지수"),
        ("KOSPI 200 지수", "코스피 이백 지수"),
        ("KOSDAQ150 지수", "코스닥 백오십 지수"),
        ("KOSDAQ 150 지수", "코스닥 백오십 지수"),
    ],
)
def test_finance_managed_lexicon_and_numeric_suffix(text: str, expected: str) -> None:
    assert production_transform(text) == expected


def test_finance_index_numeric_suffix_full_claim_blocks_partial_p500() -> None:
    output = transform_with_trace("S&P500 지수")

    assert output.normalized_text == "에스앤피 오백 지수"
    assert any(
        claim.owner == "finance_index" and claim.span.start == 0 and claim.span.end == 6
        for claim in output.trace.claim_logs
    )
    assert not any(claim.owner == "single_letter_alnum_code" for claim in output.trace.claim_logs)
    assert "S&피 오백" not in output.normalized_text


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("TTS", "티티에스"),
        ("API", "에이피아이"),
        ("JSON", "제이슨"),
        ("CPU", "씨피유"),
        ("GPU", "지피유"),
        ("USB", "유에스비"),
        ("PDF", "피디에프"),
        ("OECD", "오이씨디"),
        ("WHO", "더블유에이치오"),
        ("FOMC", "에프오엠씨"),
        ("NASDAQ", "나스닥"),
        ("S&P", "에스앤피"),
        ("KOSPI", "코스피"),
        ("KOSDAQ", "코스닥"),
    ],
)
def test_managed_lexicon_representative_entries_are_span_dictionary(
    surface: str, expected: str
) -> None:
    assert DICTIONARY_READINGS[surface] == expected
    assert production_transform(f"{surface} 항목") == f"{expected} 항목"
    trace = transform_with_trace(f"{surface} 항목").trace
    assert any(claim.owner == "dictionary" for claim in trace.claim_logs)


@pytest.mark.parametrize("text", ["USB300", "APIv2", "A12.3B", "OpenAI"])
def test_managed_lexicon_does_not_expand_broad_fallbacks(text: str) -> None:
    assert production_transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/path/S&P500/log", "/path/S&P500/log"),
        ("https://example.com?q=S&P500", "https://example.com?q=S&P500"),
        ('{"index":"S&P500"}', '{"index":"S&P500"}'),
        ("`S&P500`", "`S&P500`"),
        ("[S&P500]", "S&P500"),
    ],
)
def test_finance_index_numeric_suffix_respects_protected_contexts(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected
