from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "03만",
        "001만",
        "3만-4만",
        "만",
        "억",
        "조",
    ],
)
def test_large_unit_atomic_preserve_and_forbidden(text: str) -> None:
    assert transform(text) == text


def test_compact_large_unit_range_uses_range_reading() -> None:
    assert transform("3~8만") == "삼에서 팔만"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3만개", "삼만-개"),
        ("12만개입니다", "십이만-개입니다"),
    ],
)
def test_large_unit_registered_counter_uses_counter_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3만abc", "삼만abc"),
        ("3만kgabc", "삼만kgabc"),
        ("2천8백28억abc", "이천팔백이십팔억abc"),
    ],
)
def test_large_unit_atomic_unregistered_english_tail_literal_preservation(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3만kg", "삼만-킬로그램"),
        ("3만 kg", "삼만-킬로그램"),
        ("3만km", "삼만-킬로미터"),
        ("3만Hz", "삼만-헤르츠"),
        ("3만m", "삼만-미터"),
        ("300만kg", "삼백만-킬로그램"),
        ("1억km", "일억-킬로미터"),
        ("3만㎏", "삼만-킬로그램"),
        ("무게는 3만kg입니다", "무게는 삼만-킬로그램입니다"),
        ('3.5만kg', '삼-쩜-오-만-킬로그램'),
        ('3.5만 kg', '삼-쩜-오-만-킬로그램'),
        ('3.5만㎡', '삼-쩜-오-만-제곱미터'),
        ('25.50억kg', '이십오-쩜-오영-억-킬로그램'),
        ('2,345.5만km', '이천삼백사십오-쩜-오-만-킬로미터'),
        ('+3.5만kg', '플러스 삼-쩜-오-만-킬로그램'),
        ('-3.5만kg', '마이너스 삼-쩜-오-만-킬로그램'),
    ],
)
def test_large_unit_registered_ascii_units_are_read(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('3.5만', '삼-쩜-오-만'),
        ('3.5만 원', '삼-쩜-오-만 원'),
    ],
)
def test_decimal_large_unit_krw_expansion_policy_v102(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-3만", "마이너스 삼만"),
        ("+3만", "플러스 삼만"),
    ],
)
def test_phase16d_signed_number_updates_former_large_unit_preserve(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
