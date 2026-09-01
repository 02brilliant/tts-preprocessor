from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01월", "일월"),
        ("03일", "삼일"),
        ("09월", "구월"),
        ("00월", "00월"),
        ("00일", "00일"),
        ("001월", "001월"),
        ("01", "01"),
        ("0012", "0012"),
    ],
)
def test_leading_zero_counter_override_only_for_month_day(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("112명", "백십이-명"),
        ("119건", "백십구-건"),
        ("112개", "백십이 개"),
        ("119명", "백십구 명"),
    ],
)
def test_emergency_ambiguous_allowed_counter_fallbacks_use_counter_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ('112명', '백십이명'),
        ('112명', '백십이명'),
        ('119개', '일일이구개'),
    ],
)
def test_emergency_counter_forbidden_signatures_do_not_appear(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3번", "3번"),
        ("3분", "3분"),
        ("3초", "삼초"),
        ("3건", "세-건"),
    ],
)
def test_unsupported_counter_nouns_use_phase11_number_suffix_fallback(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ('세 번', '3번'),
        ('세 분', '3분'),
        ('3초', '세 초'),
        ('3건', '삼건'),
    ],
)
def test_unsupported_counter_nouns_do_not_use_native_counter(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden


@pytest.mark.parametrize(
    "text",
    ["21명abc", "21명kg", "03명"],
)
def test_counter_full_consume_unsafe_patterns_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-3명", "마이너스 삼 명"),
        ("+3명", "플러스 삼 명"),
    ],
)
def test_signed_person_counter_uses_residual_reading(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_decimal_registered_counter_suffix_now_transforms() -> None:
    assert transform("3.5명") == '삼-쩜-오-명'


def test_phase36b_comma_counter_form_now_transforms() -> None:
    assert transform("1,000명") == "천-명"
