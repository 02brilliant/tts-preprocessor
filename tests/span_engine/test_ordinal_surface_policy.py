from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.ordinal import ordinal_reading
from engine.span_engine.tokenizer import tokenize_immutable_spans
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7번째", "일곱-번째"),
        ("7 번째", "일곱-번째"),
        ("1번째", "첫-번째"),
        ("5번째", "다섯-번째"),
        ("39번째", "서른아홉-번째"),
        ("40번째", "사십-번째"),
        ('2.5번째', '이-쩜-오-번째'),
        ('2.5 번째', '이-쩜-오-번째'),
        ("제7번째", "제-일곱-번째"),
        ("제 7번째", "제-일곱-번째"),
        ("7번째만", "일곱-번째만"),
        ("7번째로", "일곱-번째로"),
        ("1번째부터 10번째까지", "첫-번째부터 열-번째까지"),
        ("7번째abc", "일곱-번째abc"),
        ("7번째 항목이다", "일곱-번째 항목이다"),
        ("7번째, 8번째", "일곱-번째, 여덟-번째"),
    ],
)
def test_ordinal_surface_reads_number_and_suffix_without_tail_gating(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "01번째",
        "0번째",
        "abc7번째",
        "v7번째",
        "A제7번째",
    ],
)
def test_ordinal_invalid_or_blocked_surfaces_preserve(text: str) -> None:
    assert transform(text) == text


def test_ordinal_tokenizer_splits_suffix_from_attached_josa() -> None:
    tokens = tokenize_immutable_spans("7번째만")
    assert [(token.kind, token.raw) for token in tokens] == [
        ("PLAIN", "7"),
        ("KOREAN_LITERAL", "번째"),
        ("KOREAN_LITERAL", "만"),
    ]


def test_ordinal_owner_claims_only_suffix_span() -> None:
    output = transform_with_trace("7번째만")
    assert output.normalized_text == "일곱-번째만"
    assert len(output.trace.claim_logs) == 1
    assert output.trace.claim_logs[0].owner == "ordinal"
    assert output.trace.claim_logs[0].span.end == 3


@pytest.mark.parametrize(
    ("raw_number", "expected"),
    [
        ('7', '일곱-번째'),
        ('2.5', '이-쩜-오-번째'),
        ('1', '첫-번째'),
        ('40', '사십-번째'),
    ],
)
def test_ordinal_reading_policy(raw_number: str, expected: str) -> None:
    assert ordinal_reading(raw_number) == expected
