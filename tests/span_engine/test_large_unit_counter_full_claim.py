from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.large_unit import parse_large_unit_integer_core_at
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1만3천개", "일만삼천 개"),
        ("1만3천개다.", "일만삼천 개다."),
        ("1만3천개는", "일만삼천 개는"),
        ("1만3천개였다", "일만삼천 개였다"),
        ("1만3천개입니다", "일만삼천 개입니다"),
        ("3만개", "삼만 개"),
        ("12만개입니다", "십이만 개입니다"),
        ("1만3천개월", "일만삼천개월"),
    ],
)
def test_large_unit_registered_counter_full_claim(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_large_unit_counter_user_reported_sentence_exact_output() -> None:
    text = (
        "1만3천개다. 1만3천 개다. 1만 3천개다. "
        "1만3천명이다. 1만3천이다. 1만3천 이다."
    )
    assert transform(text) == (
        "일만삼천 개다. 일만삼천 개다. 일만 삼천 개다. "
        "일만삼천 명이다. 일만삼천이다. 일만삼천 이다."
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1만3천 개다.", "일만삼천 개다."),
        ("1만 3천개다.", "일만 삼천 개다."),
        ("1만3천명이다.", "일만삼천 명이다."),
        ("1만3천이다.", "일만삼천이다."),
        ("1만3천 이다.", "일만삼천 이다."),
        ("1만3천여 명", "일만삼천여 명"),
        ("6천400명", "육천사백 명"),
        ("꽃이 만개했다.", "꽃이 만개했다."),
        ("만개다.", "만개다."),
    ],
)
def test_large_unit_counter_existing_boundaries_remain_stable(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "1만3천개abc",
        "1만3천개/log",
        "A1만3천개",
        "`1만3천개`",
        "01만3천개",
        "1만3천개발",
        "1만3천개시",
    ],
)
def test_large_unit_counter_unsafe_or_protected_tail_preserves(text: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert not any(
        claim.owner in {"counter_noun", "number"}
        for claim in output.trace.claim_logs
    )


def test_large_unit_counter_trace_and_provenance() -> None:
    output = transform_with_trace("1만3천개다.")

    assert output.normalized_text == "일만삼천 개다."
    assert [
        (
            claim.owner,
            claim.surface_type,
            claim.reason,
            claim.span.start,
            claim.span.end,
        )
        for claim in output.trace.claim_logs
    ] == [
        (
            "counter_noun",
            "COUNTER_SURFACE",
            "counter_large_unit_core_full_consume",
            0,
            5,
        )
    ]
    assert not any(
        claim.reason == "invalid_large_unit_numeric_surface_preserve"
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.owner == "counter_noun"
        and piece.provenance == "GENERATED_READING"
        and piece.text == "일만삼천"
        for piece in output.render_pieces
    )
    assert any(
        piece.owner == "counter_noun"
        and piece.provenance == "ORIGINAL_KOREAN"
        and piece.text == "개"
        for piece in output.render_pieces
    )
    assert all(log.passed for log in output.trace.validation_logs)


@pytest.mark.parametrize(
    ("text", "end", "reading", "value"),
    [
        ("3만개", 2, "삼만", 30_000),
        ("1만3천개", 4, "일만삼천", 13_000),
        (
            "1억2천3백만4천5백명",
            11,
            "일억이천삼백만사천오백",
            123_004_500,
        ),
    ],
)
def test_large_unit_integer_core_parser_is_reusable(
    text: str, end: int, reading: str, value: int
) -> None:
    parsed = parse_large_unit_integer_core_at(text, 0)

    assert parsed is not None
    assert (parsed.end, parsed.reading, parsed.value) == (end, reading, value)
