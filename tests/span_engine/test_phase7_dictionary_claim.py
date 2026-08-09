from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI", "에이아이"),
        ("FTA", "에프티에이"),
        ("KOSPI", "코스피"),
        ("TTS", "티티에스"),
        ("API", "에이피아이"),
        ("OpenAI", "오픈 에이아이"),
        ("L-SAM", "엘-샘"),
        ("M-SAM", "엠-샘"),
        ("AI는 중요하다", "에이아이는 중요하다"),
        ("FTA는 적용됐다", "에프티에이는 적용됐다"),
        ("KOSPI가 올랐다", "코스피가 올랐다"),
        ("PDF 파일", "피디에프 파일"),
        ("JSON API", "제이슨 에이피아이"),
        ("FTA은 적용됐다", "에프티에이는 적용됐다"),
        ("AI이 적용됐다", "에이아이이 적용됐다"),
        ("PDF파일", "피디에프파일"),
    ],
)
def test_dictionary_fixed_lexical_transform(text: str, expected: str) -> None:
    assert transform(text) == expected
    assert transform_with_trace(text).normalized_text == expected


@pytest.mark.parametrize(
    "text",
    ["AI3", "3AI", "APIv2", "JSONParser"],
)
def test_dictionary_does_not_partial_consume_inside_mixed_tokens(text: str) -> None:
    assert transform(text) == text


def test_fallback_covered_acronym_full_consumes_without_dictionary_partial_split() -> None:
    output = transform_with_trace("AIA")

    assert output.normalized_text == "에이아이에이"
    assert any(claim.owner == "acronym_fallback" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "dictionary" for claim in output.trace.claim_logs)


def test_dictionary_does_not_partial_consume_inside_multi_letter_hyphen_code() -> None:
    output = transform_with_trace("AI-1")

    assert output.normalized_text == "AI-1"
    assert not any(claim.owner == "two_block_hyphen_code" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "single_letter_alnum_code" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "dictionary" for claim in output.trace.claim_logs)
