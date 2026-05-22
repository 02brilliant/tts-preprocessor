from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25℃", "이십오도"),
        ("25ºC", "이십오도"),
        ("25℉", "화씨 이십오도"),
        ("25ºF", "화씨 이십오도"),
        ("25°", "이십오도"),
        ("25º", "이십오도"),
    ],
)
def test_phase35d_unsigned_temperature_and_degree_have_no_sign_prefix(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-2.5℃", "영하 이쩜오도"),
        ("-2.5ºC", "영하 이쩜오도"),
        ("-2.5℉", "화씨 영하 이쩜오도"),
        ("-2.5ºF", "화씨 영하 이쩜오도"),
        ("-2.5º", "영하 이쩜오도"),
    ],
)
def test_phase35d_negative_temperature_like_degree(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("온도-2.5℃", "온도영하 이쩜오도"),
        ("온도+3℃", "온도영상 삼도"),
        ("온도-2.5℉", "온도화씨 영하 이쩜오도"),
        ("온도+3℉", "온도화씨 영상 삼도"),
        ("온도-2.5º", "온도영하 이쩜오도"),
        ("온도+3º", "온도영상 삼도"),
    ],
)
def test_phase35d_korean_attached_signed_temperature_full_consumes(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3℃", "영상 삼도"),
        ("+3ºC", "영상 삼도"),
        ("+3℉", "화씨 영상 삼도"),
        ("+3ºF", "화씨 영상 삼도"),
        ("+3º", "영상 삼도"),
    ],
)
def test_phase35d_positive_temperature_like_degree(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3°", "플러스 삼도"),
        ("-3°", "마이너스 삼도"),
        ("3°", "삼도"),
    ],
)
def test_phase35d_angle_degree_keeps_existing_signed_degree_policy(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+ 3℃", "+ 삼도"),
        ("- 3℃", "- 삼도"),
        ("+ 3°", "+ 삼도"),
        ("- 3°", "- 삼도"),
        ("+ 3º", "+ 삼도"),
        ("- 3º", "- 삼도"),
    ],
)
def test_phase35d_spaced_signs_do_not_full_consume_as_signed_surfaces(
    text: str, expected: str
) -> None:
    result = transform(text)

    assert result == expected
    assert not result.startswith(("영상 ", "영하 ", "플러스 ", "마이너스 "))


@pytest.mark.parametrize(
    "text",
    [
        "2.5ºCat",
        "30ºCtest",
        "40℉abc",
        "+3ºCat",
        "-3ºCat",
        "-2.5℃abc",
        "A-2.5º",
        "A-2.5℃",
        "x-2.5º",
        "x-2.5℉",
        "B-2.5º",
    ],
)
def test_phase35d_temperature_and_bare_degree_unsafe_tails_preserve(
    text: str,
) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3°", "플러스 삼도"),
        ("-3°", "마이너스 삼도"),
        ("+3º", "영상 삼도"),
        ("-3º", "영하 삼도"),
    ],
)
def test_phase35d_existing_signed_degree_and_bare_o_regression_guard(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
