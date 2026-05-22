from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "03만",
        "001만",
        "3만-4만",
        "3~8만",
        "만",
        "억",
        "조",
        "3만개",
        "12만개입니다",
    ],
)
def test_large_unit_atomic_preserve_and_forbidden(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3만abc", "삼만abc"),
        ("3만kg", "삼만kg"),
    ],
)
def test_large_unit_atomic_english_tail_literal_preservation(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.5만", "삼쩜오 만"),
        ("3.5만 원", "삼쩜오 만 원"),
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
