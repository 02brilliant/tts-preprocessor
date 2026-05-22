from __future__ import annotations

import pytest

from engine.span_engine import ShadowUnit, SourceSpan
from engine.span_engine.shadow import build_shadow_buffer
from engine.span_engine.tokenizer import tokenize_immutable_spans


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("안녕하세요", [ShadowUnit("KOREAN_LITERAL", "안녕하세요", SourceSpan(0, 5))]),
        (
            "전문  가",
            [
                ShadowUnit("KOREAN_LITERAL", "전문", SourceSpan(0, 2)),
                ShadowUnit("KOREAN_SPACE", "  ", SourceSpan(2, 4)),
                ShadowUnit("KOREAN_LITERAL", "가", SourceSpan(4, 5)),
            ],
        ),
        (
            "안녕하세요,",
            [
                ShadowUnit("KOREAN_LITERAL", "안녕하세요", SourceSpan(0, 5)),
                ShadowUnit("KOREAN_PUNCT", ",", SourceSpan(5, 6)),
            ],
        ),
        (
            "AI는 123입니다",
            [
                ShadowUnit("KOREAN_LITERAL", "는", SourceSpan(2, 3)),
                ShadowUnit("KOREAN_SPACE", " ", SourceSpan(3, 4)),
                ShadowUnit("KOREAN_LITERAL", "입니다", SourceSpan(7, 10)),
            ],
        ),
        ("3~8cm", []),
        (
            "[[K:사용자입력]]",
            [ShadowUnit("KOREAN_LITERAL", "사용자입력", SourceSpan(4, 9))],
        ),
        ("ㄱㄴㄷ", []),
    ],
)
def test_build_shadow_buffer_keeps_only_original_preservation_targets(
    raw_text: str, expected: list[ShadowUnit]
) -> None:
    tokens = tokenize_immutable_spans(raw_text)

    assert build_shadow_buffer(tokens) == expected


def test_shadow_units_preserve_token_order_span_and_raw() -> None:
    tokens = tokenize_immutable_spans("전문  가")
    shadow = build_shadow_buffer(tokens)

    assert [(unit.kind, unit.raw, unit.span) for unit in shadow] == [
        ("KOREAN_LITERAL", "전문", SourceSpan(0, 2)),
        ("KOREAN_SPACE", "  ", SourceSpan(2, 4)),
        ("KOREAN_LITERAL", "가", SourceSpan(4, 5)),
    ]
