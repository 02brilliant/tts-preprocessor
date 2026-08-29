from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "40℉abc",
        "30ºCtest",
        "2.5ºCat",
        "2.5ºFahrenheit",
        "45㎡abc",
        "0.5㎡abc",
        "45㎥abc",
        "5Hzabc",
        "5hzabc",
        "15.2km/La",
        "15.2km/lab",
        "3km/speed",
        "90km/hour",
        "250m/Lite",
    ],
)
def test_unit_like_surfaces_with_unsafe_ascii_tail_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("40℉", "화씨 사십도"),
        ("30ºC", "삼십도"),
        ("25℃", "이십오도"),
        ("45㎡", "사십오-제곱미터"),
        ("45㎥", "사십오-세제곱미터"),
        ("5Hz", "오-헤르츠"),
        ("90km/h", "시속 구십 킬로미터"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
    ],
)
def test_supported_unit_and_compound_unit_readings_remain(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[40℉abc]", "40℉abc"),
        ("[30ºCtest]", "30ºCtest"),
        ("[45㎡abc]", "45㎡abc"),
        ("[15.2km/La]", "15.2km/La"),
    ],
)
def test_bracket_protected_unit_like_tails_remain_raw(text: str, expected: str) -> None:
    assert transform(text) == expected
