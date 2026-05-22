from __future__ import annotations

import pytest

from engine.span_engine.tokenizer import (
    tokenize_immutable_spans,
    validate_token_coverage,
)


TOKEN_COVERAGE_CASES = [
    "",
    "abc",
    "안녕하세요",
    "전문  가",
    "안녕하세요,",
    "안녕하세요 , 반갑습니다",
    "AI는 123입니다",
    "회의는 13:05에 시작한다",
    "12.3 비상계엄",
    "3~8cm",
    "가격은 [3kg]입니다",
    "비용은 (약) 3만원입니다",
    "FTA은 적용됐다",
    "AI이 적용됐다",
    "유로을 입력했다",
    "종로3가",
    "1-1-9",
    "123-456-7890",
    "pH 7.4",
    "€50을 냈다",
    "-2.5℃",
    "ㄱㄴㄷ",
    "전문\n가",
    "emoji 😀 테스트",
    "zero\u200bwidth",
    "[[K:사용자입력]]",
    "{{S:사용자입력}}",
]


@pytest.mark.parametrize("raw_text", TOKEN_COVERAGE_CASES)
def test_tokenize_immutable_spans_covers_raw_text_without_gaps(raw_text: str) -> None:
    tokens = tokenize_immutable_spans(raw_text)

    validate_token_coverage(raw_text, tokens)
    assert "".join(token.raw for token in tokens) == raw_text
    for token in tokens:
        assert raw_text[token.span.start : token.span.end] == token.raw


def test_validate_token_coverage_rejects_gap_or_bad_slice() -> None:
    tokens = tokenize_immutable_spans("abc")
    tokens[0].raw = "x"

    with pytest.raises(ValueError):
        validate_token_coverage("abc", tokens)
