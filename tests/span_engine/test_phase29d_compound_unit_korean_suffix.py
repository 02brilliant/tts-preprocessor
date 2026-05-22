from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90km/h이다", "시속 구십 킬로미터이다"),
        ("15.2km/L이다", "리터당 십오쩜이 킬로미터이다"),
        ("15.2km/l이며", "리터당 십오쩜이 킬로미터이며"),
        ("3km/s까지", "초속 삼 킬로미터까지"),
        ("5Hz급", "오 헤르츠급"),
        ("5hz급", "오 헤르츠급"),
    ],
)
def test_compound_and_simple_units_allow_safe_korean_suffixes(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "15.2km/lab",
        "90km/hour",
        "5Hzabc",
        "5hzabc",
    ],
)
def test_compound_and_simple_units_still_preserve_unsafe_ascii_tails(
    text: str,
) -> None:
    assert transform(text) == text
