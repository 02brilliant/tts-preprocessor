from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "USD20abc",
        "US D20",
        "AUD 20",
        "BTC 1",
        "$",
        "USD",
        "€abc",
        "$100kg",
    ],
)
def test_unsupported_currency_patterns_preserve(text: str) -> None:
    assert transform(text) == text


def test_registered_comma_currency_symbol_transforms() -> None:
    assert transform("$1,200") == "천이백 달러"


@pytest.mark.parametrize(
    "text",
    [
        "50kgabc",
        "001kg",
        "mL",
        "kg",
        "10A",
        "10V",
        "50kg/m",
        "http://x/50kg",
    ],
)
def test_unsupported_unit_patterns_preserve(text: str) -> None:
    assert transform(text) == text


def test_single_letter_alnum_code_updates_former_unit_preserve_case() -> None:
    assert transform("A10") == "에이 십"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("50 kg", "오십 킬로그램"),
        ("1,000kg", "천 킬로그램"),
        ("3.5kg", "삼쩜오 킬로그램"),
    ],
)
def test_phase36b_space_and_comma_unit_forms_now_transform(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("$1.25", "$일쩜이오"),
        ("USD20abc", "이십 달러abc"),
        ("$100kg", "백 달러kg"),
        ("50kgabc", "오십 킬로그램abc"),
        ("90km/h", "구십 킬로미터/h"),
    ],
)
def test_unit_currency_forbidden_partial_signatures_do_not_appear(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
