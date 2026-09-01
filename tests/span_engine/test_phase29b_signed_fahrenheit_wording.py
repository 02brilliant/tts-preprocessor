from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('-2.5℉', '화씨 영하 이-쩜-오도'),
        ('-2.5ºF', '화씨 영하 이-쩜-오도'),
        ('-2.5°F', '화씨 영하 이-쩜-오도'),
    ],
)
def test_signed_fahrenheit_includes_fahrenheit_prefix_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25℉", "화씨 이십오도"),
        ("25ºF", "화씨 이십오도"),
        ("25°F", "화씨 이십오도"),
        ('-2.5℃', '영하 이-쩜-오도'),
        ('-2.5ºC', '영하 이-쩜-오도'),
        ('-2.5°C', '영하 이-쩜-오도'),
    ],
)
def test_unsigned_fahrenheit_and_signed_celsius_regressions(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
