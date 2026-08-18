from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("오전 9시 6분께", "오전 아홉 시 육분께"),
        ("9시6분께", "아홉 시 육분께"),
        ("5분 15초께", "오분 십오초께"),
        ("5분15초께", "오분 십오초께"),
        ("9시 5분 15초께", "아홉 시 오분 십오초께"),
        ("9시5분15초께", "아홉 시 오분 십오초께"),
    ],
)
def test_structured_time_allows_approximate_kke_tail(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "6분께",
        "6분께서",
        "3분개발",
    ],
)
def test_non_structured_minute_kke_tail_preserves(text: str) -> None:
    assert transform(text) == text


def test_hour_only_kke_tail_uses_clock_hour_owner() -> None:
    assert transform("9시께") == "아홉 시께"


def test_structured_time_kke_trace_uses_time_owner_not_preserve() -> None:
    output = transform_with_trace("오전 9시 6분께")

    assert output.normalized_text == "오전 아홉 시 육분께"
    assert [
        (claim.owner, claim.reason)
        for claim in output.trace.claim_logs
    ] == [
        ("time", "time_hour_korean_context"),
        ("time", "time_minute_korean_context"),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("6천", "육천"),
        ("6천5백", "육천오백"),
        ("6천400", "육천사백"),
        ("5천830", "오천팔백삼십"),
        ("1천2백3십", "일천이백삼십"),
        ("1천2백3십4", "일천이백삼십사"),
        ("2만3천", "이만삼천"),
        ("3천만5천", "삼천만오천"),
        ("1억2천3백만4천5백", "일억이천삼백만사천오백"),
        ("5천830,", "오천팔백삼십,"),
        ("값은6천이다", "값은육천이다"),
        ("값은6천5백이다", "값은육천오백이다"),
        ("값은5천830이다", "값은오천팔백삼십이다"),
        ("값은2만3천이다", "값은이만삼천이다"),
        ("값은3천만5천이다", "값은삼천만오천이다"),
        ("금액은6천원이다", "금액은육천 원이다"),
        ("금액은6천5백원이다", "금액은육천오백 원이다"),
        ("금액은2만3천원이다", "금액은이만삼천 원이다"),
        ("금액은3천만5천원이다", "금액은삼천만오천 원이다"),
        ("수량은6천개다", "수량은육천 개다"),
    ],
)
def test_mixed_integer_full_core_reads_across_safe_hangul_boundaries(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "A6천",
        "A가6천",
        "A-가6천",
        "foo$6천",
        "문장/가6천",
        "6천abc",
        "가6천이다/log",
        "01천",
        "1천2천",
        "5천8300",
        "5백830",
            "5십30",
            "https://example.com/6천",
        "`6천5백`",
        "A5천830.13",
        "01천830.13",
        "5천830.13abc",
        "5천830.13.2",
        "https://example.com/5천830.13",
        "`5천830.13`",
    ],
)
def test_mixed_integer_unsafe_or_malformed_surfaces_preserve(text: str) -> None:
    assert transform(text) == text


def test_prefixed_ordinal_reads_sino_before_mixed_integer_hangul() -> None:
    assert transform("제6천원") == "제 육천원"


def test_mixed_integer_trace_full_claim_and_original_unit_provenance() -> None:
    output = transform_with_trace("값은6천5백이다")

    assert output.normalized_text == "값은육천오백이다"
    assert [
        (claim.owner, claim.reason)
        for claim in output.trace.claim_logs
    ] == [
        ("mixed_integer_atomic", "mixed_integer_small_unit_full_consume"),
    ]
    assert [
        (piece.text, piece.provenance)
        for piece in output.render_pieces
        if piece.owner == "mixed_integer_atomic"
    ] == [
        ("육", "GENERATED_READING"),
        ("천", "ORIGINAL_KOREAN"),
        ("오", "GENERATED_READING"),
        ("백", "ORIGINAL_KOREAN"),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_mixed_decimal_full_claim_and_provenance() -> None:
    output = transform_with_trace("값은5천830.13이다")

    assert output.normalized_text == "값은오천팔백삼십쩜일삼이다"
    assert [
        (claim.owner, claim.reason)
        for claim in output.trace.claim_logs
    ] == [
        (
            "mixed_decimal_atomic",
            "mixed_integer_small_unit_decimal_full_consume",
        ),
    ]
    assert [
        (piece.text, piece.provenance)
        for piece in output.render_pieces
        if piece.owner == "mixed_decimal_atomic"
    ] == [
        ("오", "GENERATED_READING"),
        ("천", "ORIGINAL_KOREAN"),
        ("팔백삼십", "GENERATED_READING"),
        ("쩜일삼", "GENERATED_READING"),
    ]
    assert all(log.passed for log in output.trace.validation_logs)


def test_user_reported_time_and_adjacent_currency_sentence() -> None:
    assert transform("오전 9시 6분께 22만원6천원이다.") == (
        "오전 아홉 시 육분께 이십이만 원육천 원이다."
    )


def test_user_reported_mixed_integer_and_decimal_sentence() -> None:
    assert transform(
        "숫자들은 5천830, 5천830이고, 마지막은 5천830.13이다."
    ) == (
        "숫자들은 오천팔백삼십, 오천팔백삼십이고, "
        "마지막은 오천팔백삼십쩜일삼이다."
    )
