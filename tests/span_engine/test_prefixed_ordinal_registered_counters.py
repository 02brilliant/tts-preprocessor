from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제2차", "제 이차"),
        ("제15권", "제 십오권"),
        ("제3장", "제 삼장"),
        ("제2차례", "제 이차례"),
        ("제2편", "제 이편"),
        ("제2판", "제 이판"),
        ("제2줄", "제 이줄"),
        ("제2칸", "제 이칸"),
    ],
)
def test_existing_prefixed_ordinal_counters(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제2문항", "제 이문항"),
        ("제2문제", "제 이문제"),
        ("제2항목", "제 이항목"),
        ("제2사례", "제 이사례"),
        ("제2장면", "제 이장면"),
        ("제2곡", "제 이곡"),
        ("제2대", "제 이대"),
        ("제2석", "제 이석"),
        ("제2표", "제 이표"),
        ("제2매", "제 이매"),
        ("제2세트", "제 이세트"),
        ("제2팩", "제 이팩"),
        ("제2봉", "제 이봉"),
        ("제2종류", "제 이종류"),
    ],
)
def test_prefixed_ordinal_new_registered_counters(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제 2문항", "제 이문항"),
        ("제 2항목", "제 이항목"),
        ("제 2대", "제 이대"),
        ("제 15권", "제 십오권"),
    ],
)
def test_prefixed_ordinal_spaced_je_number(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2문항", "두 문항"),
        ("40문항", "사십 문항"),
        ("101문항", "백일 문항"),
        ("2항목", "두 항목"),
        ("2대", "2대"),
        ("40대", "사십 대"),
    ],
)
def test_plain_counter_reading_unchanged(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("A제2문항", "A제2문항"),
        ("A제 2문항", "A제 두 문항"),
        ("제2문항abc", "제 이문항abc"),
        ("제2문항A", "제 이문항A"),
        ("제2항목abc", "제 이항목abc"),
        ("제2-문항", "제2-문항"),
        ("제2G", "제2G"),
        ("제2.5문항", "제 이쩜오문항"),
    ],
)
def test_prefixed_ordinal_unsafe_preserve(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_prefixed_ordinal_reads_sino_before_arbitrary_hangul_suffix() -> None:
    assert transform("제2아무말") == "제 이아무말"
