from __future__ import annotations

import pytest

from engine.span_engine import transform
from engine.span_engine.number import number_to_korean_under_10000


@pytest.mark.parametrize(
    ("value", "reading"),
    [
        (0, "영"),
        (1, "일"),
        (9, "구"),
        (10, "십"),
        (11, "십일"),
        (20, "이십"),
        (21, "이십일"),
        (99, "구십구"),
        (100, "백"),
        (101, "백일"),
        (110, "백십"),
        (123, "백이십삼"),
        (1000, "천"),
        (1010, "천십"),
        (2025, "이천이십오"),
    ],
)
def test_number_to_korean_under_10000(value: int, reading: str) -> None:
    assert number_to_korean_under_10000(value) == reading


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("123", "백이십삼"),
        ("2025", "이천이십오"),
        ("AI 123", "에이아이 백이십삼"),
        ("123입니다", "백이십삼입니다"),
        ("123.", "백이십삼."),
        ("가격 1000", "가격 천"),
        ("1,234", "천이백삼십사"),
    ],
)
def test_minimal_number_parser(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "0012",
        "01",
        "1e6",
        "3.2E-4",
        "123abc",
        "abc123",
        "123-456",
    ],
)
def test_unsupported_number_patterns_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-5", "마이너스 오"),
        ("+5", "플러스 오"),
    ],
)
def test_phase16d_signed_number_updates_former_unsupported_number_patterns_preserve(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_phase10_unit_owner_prevents_number_partial_for_unit_case() -> None:
    assert transform("50kg") == "오십-킬로그램"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21명", "스물한-명"),
        ("3월", "삼월"),
        ("3~8", "삼에서 팔"),
    ],
)
def test_phase11_and_phase12_owners_update_former_number_preserve_cases(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
