from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


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
        ('-2.5℃', '영하 이-쩜-오도'),
        ('-2.5ºC', '영하 이-쩜-오도'),
        ('-2.5℉', '화씨 영하 이-쩜-오도'),
        ('-2.5ºF', '화씨 영하 이-쩜-오도'),
        ('-2.5º', '영하 이-쩜-오도'),
    ],
)
def test_phase35d_negative_temperature_like_degree(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('온도-2.5℃', '온도영하 이-쩜-오도'),
        ("온도+3℃", "온도영상 삼도"),
        ('온도-2.5℉', '온도화씨 영하 이-쩜-오도'),
        ("온도+3℉", "온도화씨 영상 삼도"),
        ('온도-2.5º', '온도영하 이-쩜-오도'),
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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+25℃보다 높다", "영상 이십오도보다 높다"),
        ("-10℃보다 낮다", "영하 십도보다 낮다"),
        ("+25℃처럼 느껴진다", "영상 이십오도처럼 느껴진다"),
        ("-10℃처럼 춥다", "영하 십도처럼 춥다"),
        ("+3℃마다 기록한다", "영상 삼도마다 기록한다"),
        ("+3℃라고 했다", "영상 삼도라고 했다"),
        ("+3℃인데 괜찮다", "영상 삼도인데 괜찮다"),
        ("+3℃라면 가능하다", "영상 삼도라면 가능하다"),
        ("+25℃테스트", "영상 이십오도테스트"),
        ("+25℃짜리", "영상 이십오도짜리"),
        ("+3°보다", "플러스 삼도보다"),
        ("+3°테스트", "플러스 삼도테스트"),
    ],
)
def test_phase35d_signed_temperature_degree_allows_hangul_leading_tails(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "+25℃abc",
        "-10℃abc",
        "+25℃v2",
        "+25℃/min",
        "-10℃/min",
        "+3°abc",
        "+3°/s",
        "A-2.5℃",
    ],
)
def test_phase35d_signed_temperature_degree_preserves_code_like_tails(
    text: str,
) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+3℃", "영상 삼도"),
        ("-3℃", "영하 삼도"),
        ("+3℃를", "영상 삼도를"),
        ("+25℃였고", "영상 이십오도였고"),
        ("-3℃였지만", "영하 삼도였지만"),
    ],
)
def test_phase35d_signed_temperature_degree_baseline_safe_tails(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "owner"),
    [
        ('+25℃보다 높다', 'signed_temperature'),
        ('+25℃테스트', 'signed_temperature'),
    ],
)
def test_phase35d_signed_temperature_degree_hangul_tail_trace_owner(
    text: str, owner: str
) -> None:
    output = transform_with_trace(text)

    assert any(claim.owner == owner for claim in output.trace.claim_logs)


@pytest.mark.parametrize(
    "text",
    [
        "+25℃abc",
        "+25℃/min",
    ],
)
def test_phase35d_signed_temperature_degree_code_like_tail_trace_preserves(
    text: str,
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert not any(
        claim.owner == "signed_temperature" for claim in output.trace.claim_logs
    )
