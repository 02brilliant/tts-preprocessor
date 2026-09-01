from __future__ import annotations

import pytest

from engine.span_engine import transform
from engine.span_engine.numeric_prosody import (
    apply_compact_group_prosody,
    apply_spaced_integer_prosody,
    chunk_fractional_digits,
    join_decimal_prosody,
    read_fractional_with_prosody,
)
from engine.span_engine.numeric_reading import read_decimal_text, read_spaced_integer_text


@pytest.mark.parametrize(
    ("fractional", "expected_chunks"),
    [
        ("567890123", ["5678", "901", "23"]),
        ("5678901234", ["5678", "9012", "34"]),
        ("56789012345", ["5678", "9012", "345"]),
        ("12345", ["123", "45"]),
        ("5", ["5"]),
        ("5678901", ["5678", "901"]),
    ],
)
def test_chunk_fractional_digits(fractional: str, expected_chunks: list[str]) -> None:
    assert chunk_fractional_digits(fractional) == expected_chunks


@pytest.mark.parametrize(
    ("fractional", "expected"),
    [
        ('567890123', '오육칠팔-구영일-이삼'),
        ('5678901234', '오육칠팔-구영일이-삼사'),
        ('56789012345', '오육칠팔-구영일이-삼사오'),
        ("5", "오"),
        ('50', '오영'),
    ],
)
def test_read_fractional_with_prosody(fractional: str, expected: str) -> None:
    assert read_fractional_with_prosody(fractional) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1234.567890123", "천이백삼십사-쩜-오육칠팔-구영일-이삼"),
        ("1234.5678901234", "천이백삼십사-쩜-오육칠팔-구영일이-삼사"),
        ("1234.56789012345", "천이백삼십사-쩜-오육칠팔-구영일이-삼사오"),
        ("1.5", "일-쩜-오"),
        ("1.50", "일-쩜-오영"),
        ("0.05", "영-쩜-영오"),
        ("12.0300405", "십이-쩜-영삼영영-사영오"),
    ],
)
def test_decimal_prosody_e2e(source: str, expected: str) -> None:
    assert transform(source) == expected
    assert read_decimal_text(source) == expected


@pytest.mark.parametrize(
    ("reading", "expected"),
    [
        ("삼천이백십삼", "삼천-이백십삼"),
        ("천이백삼십사", "천이백삼십사"),
        ("만", "만"),
        ("일", "일"),
    ],
)
def test_apply_compact_group_prosody(reading: str, expected: str) -> None:
    assert apply_compact_group_prosody(reading) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("334억 8천만 3213", "삼백삼십사억 팔천만 삼천-이백십삼"),
        ("123,456", "십이만 삼천-사백오십육"),
    ],
)
def test_spaced_integer_prosody_e2e(source: str, expected: str) -> None:
    assert transform(source) == expected


def test_apply_spaced_integer_prosody_on_plain_spaced_reading() -> None:
    assert apply_spaced_integer_prosody("만 이천삼백사십오") == "만 이천삼백사십오"
    assert apply_spaced_integer_prosody("십이만 삼천사백오십육") == "십이만 삼천-사백오십육"


def test_read_spaced_integer_text_applies_group_prosody() -> None:
    assert read_spaced_integer_text("123456") == "십이만 삼천-사백오십육"
