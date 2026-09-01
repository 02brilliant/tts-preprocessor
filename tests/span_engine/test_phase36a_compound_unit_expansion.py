from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('8.5m/min', '분속 팔쩜오 미터'),
        ('8.5m／min', '분속 팔쩜오 미터'),
        ("250m/L", "리터당 이백오십 미터"),
        ("250m/l", "리터당 이백오십 미터"),
        ("250m／L", "리터당 이백오십 미터"),
        ("250m／l", "리터당 이백오십 미터"),
        ("1,000m/min", "분속 천 미터"),
        ("1,250m/L", "리터당 천이백오십 미터"),
    ],
)
def test_phase36a_new_compound_unit_readings(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_phase36a_new_compound_units_inside_korean_sentence() -> None:
    text = "속도와 연비 문단에는 8.5m/min, 250m/L, 250m/l을 넣었다."
    expected = "속도와 연비 문단에는 분속 팔쩜오 미터, 리터당 이백오십 미터, 리터당 이백오십 미터를 넣었다."
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90km/h", "시속 구십 킬로미터"),
        ('15.2km/L', '리터당 십오쩜이 킬로미터'),
        ('15.2km/l', '리터당 십오쩜이 킬로미터'),
        ('15.2㎞/ℓ', '리터당 십오쩜이 킬로미터'),
        ("3km/s", "초속 삼 킬로미터"),
        ("3㎞/s", "초속 삼 킬로미터"),
        ("5cm/s", "초속 오 센티미터"),
    ],
)
def test_phase36a_existing_compound_unit_regression(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "8.5m/minute",
        "250m/Lite",
        "250m/lab",
        "3km/speed",
        "m/min",
        "m/L",
        "km/L",
        "km/s",
    ],
)
def test_phase36a_compound_unit_preserve_cases(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "8.5m／minute",
        "250m／Lite",
    ],
)
def test_phase36a_compound_unit_fullwidth_slash_unsafe_preserve(
    text: str,
) -> None:
    assert transform(text) == text
