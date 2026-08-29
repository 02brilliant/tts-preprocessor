from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


def test_batch5_square_bracket_currency_is_absolute_preserve() -> None:
    text = "가격은 [₩1200]입니다"
    output = transform_with_trace(text)

    assert output.normalized_text == "가격은 ₩1200입니다"
    assert [
        (claim.owner, claim.claim_type, claim.surface_type, claim.reason)
        for claim in output.trace.claim_logs
    ] == [
        ("bracket", "preserve", "PROTECTED_LITERAL_SURFACE", "square_bracket_protection")
    ]
    assert not any(claim.owner == "currency" for claim in output.trace.claim_logs)


def test_batch5_unprotected_currency_still_transforms() -> None:
    text = "가격은 ₩1200입니다"
    output = transform_with_trace(text)
    assert output.normalized_text == "가격은 천이백-원입니다"
    assert any(
        claim.owner == "currency"
        and claim.surface_type == "CURRENCY_SURFACE"
        and claim.reason == "currency_symbol_with_amount"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("$-10", "마이너스 십-달러"),
        ("-$10", "마이너스 십-달러"),
        ("$10", "십-달러"),
        ("-10 USD", "마이너스 십-달러"),
        ("KRW-10", "마이너스 십-원"),
    ],
)
def test_batch5_registered_signed_currency_forms(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert any(
        claim.owner == "currency"
        and claim.surface_type == "CURRENCY_SURFACE"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    "text",
    ["$--10", "$  -10", "+-$10", "$-10abc", "-KRW10"],
)
def test_batch5_invalid_signed_currency_does_not_leak_numeric_fallback(
    text: str,
) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.030040", "십이쩜영삼영영사영"),
        ("12.0300405", "십이쩜영삼영영사영오"),
        ("12.03004050", "십이쩜영삼영영사영오영"),
    ],
)
def test_batch5_decimal_fraction_length_is_unbounded_and_zero_exact(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert any(
        claim.owner == "decimal"
        and claim.surface_type == "DECIMAL_SURFACE"
        and claim.reason == "decimal_match"
        and (claim.span.start, claim.span.end) == (0, len(text))
        for claim in output.trace.claim_logs
    )


def test_batch5_a112_is_single_letter_code_not_emergency_or_partial_number() -> None:
    text = "A112"
    output = transform_with_trace(text)
    assert output.normalized_text == "에이 백십이"
    assert [
        (claim.owner, claim.surface_type, claim.reason, claim.span.start, claim.span.end)
        for claim in output.trace.claim_logs
    ] == [
        (
            "single_letter_alnum_code",
            "SINGLE_LETTER_ALNUM_CODE_SURFACE",
            "single_letter_uppercase_alnum_code_full_consume",
            0,
            4,
        )
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A0112", "A0112"),
        ("AA112", "AA112"),
        ("A 112", "A 백십이"),
        ("긴급번호 112", "긴급번호 일일이"),
        ("112명", "백십이-명"),
    ],
)
def test_batch5_code_emergency_and_general_number_boundaries(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_batch5_bracket_and_compound_unit_claims_are_independent() -> None:
    text = "가격은 [€1,234.56]이고 연비는 15.2km/L다"
    output = transform_with_trace(text)

    assert output.normalized_text == "가격은 €1,234.56이고 연비는 리터당 십오쩜이 킬로미터다"
    assert [claim.owner for claim in output.trace.claim_logs] == [
        "bracket",
        "compound_slash_unit",
    ]
    assert output.trace.claim_logs[0].reason == "square_bracket_protection"
    assert output.trace.claim_logs[1].reason == "compound_slash_unit_inventory_match"
