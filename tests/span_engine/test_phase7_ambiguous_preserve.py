from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "OpenAI",
        "USB3",
        "1e6",
        "3.2E-4",
        "1-1-9",
    ],
)
def test_ambiguous_or_unsupported_inputs_preserve(text: str) -> None:
    if text == "1-1-9":
        assert transform(text) == "일 일 구"
    else:
        assert transform(text) == text


def test_two_block_hyphen_code_updates_former_phase7_preserve_case() -> None:
    assert transform("A-1") == "에이 원"


def test_strong_bare_time_like_updates_former_phase7_preserve_case() -> None:
    assert transform("13:05") == "십삼시 오분"


def test_phase10_unit_updates_former_phase7_preserve_case() -> None:
    assert transform("50kg") == "오십 킬로그램"


def test_phase11_counter_updates_former_phase7_preserve_case() -> None:
    assert transform("21명") == "스물한 명"


def test_phase12_range_updates_former_phase7_preserve_case() -> None:
    assert transform("3~8cm") == "삼에서 팔 센티미터"


def test_phase13_date_updates_former_phase7_preserve_case() -> None:
    assert transform("2025-01-03") == "이천이십오년 일월 삼일"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[3kg]", "3kg"),
        ("(약) 3만원", "삼만 원"),
    ],
)
def test_phase9_bracket_filter_updates_former_phase7_preserve_cases(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("OpenAI", "Open에이아이"),
        ("USB3", "유에스비삼"),
        ("A-1", "에이-일"),
        ("3~8cm", "삼~8cm"),
        ("50kg", "오십kg"),
        ("21명", "이십일명"),
        ("[3kg]", "[삼 킬로그램]"),
    ],
)
def test_forbidden_partial_outputs_do_not_appear(text: str, forbidden: str) -> None:
    assert transform(text) != forbidden


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.14", "삼쩜일사"),
        ("12.3 비상계엄", "십이삼 비상계엄"),
    ],
)
def test_phase28a_normalized_patterns(text: str, expected: str) -> None:
    # Phase 28B: Expected to fail until Phase 28C
    assert transform(text) == expected
