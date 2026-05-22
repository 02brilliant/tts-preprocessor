from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,250m", "천이백오십 미터"),
        ("1,250 m", "천이백오십 미터"),
        ("1,250km", "천이백오십 킬로미터"),
        ("1,250 km", "천이백오십 킬로미터"),
        ("1,200kg", "천이백 킬로그램"),
        ("1,200 kg", "천이백 킬로그램"),
    ],
)
def test_phase36b_valid_comma_simple_units(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,000MB", "천 메가바이트"),
        ("1,000 MB", "천 메가바이트"),
        ("1,000GB", "천 기가바이트"),
        ("1,000 GB", "천 기가바이트"),
        ("1,000Hz", "천 헤르츠"),
        ("1,000 Hz", "천 헤르츠"),
        ("1,000MHz", "천 메가헤르츠"),
        ("1,000 MHz", "천 메가헤르츠"),
    ],
)
def test_phase36b_valid_comma_data_and_frequency_units(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,330원", "천삼백삼십 원"),
        ("1,330 원", "천삼백삼십 원"),
        ("₩1,330", "천삼백삼십 원"),
        ("₩ 1,330", "천삼백삼십 원"),
        ("$1,234.56", "천이백삼십사쩜오육 달러"),
        ("$ 1,234.56", "천이백삼십사쩜오육 달러"),
        ("€1,234", "천이백삼십사 유로"),
        ("€ 1,234", "천이백삼십사 유로"),
    ],
)
def test_phase36b_valid_comma_currency(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,200건", "천이백 건"),
        ("1,200 건", "천이백 건"),
        ("8,500명", "팔천오백 명"),
        ("8,500 명", "팔천오백 명"),
        ("1,200점", "천이백 점"),
        ("1,200 점", "천이백 점"),
    ],
)
def test_phase36b_valid_comma_counters(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25 ℃", "이십오도"),
        ("-2.5 ℃", "영하 이쩜오도"),
        ("+3 ℃", "영상 삼도"),
        ("25 ℉", "화씨 이십오도"),
        ("-2.5 ℉", "화씨 영하 이쩜오도"),
        ("+3 ℉", "화씨 영상 삼도"),
    ],
)
def test_phase36b_temperature_one_space(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,000km/h", "시속 천 킬로미터"),
        ("1,000 km/h", "시속 천 킬로미터"),
        ("1,000m/s", "초속 천 미터"),
        ("1,000 m/s", "초속 천 미터"),
        ("1,000m/min", "분속 천 미터"),
        ("1,000 m/min", "분속 천 미터"),
        ("1,000km/L", "리터당 천 킬로미터"),
        ("1,000 km/L", "리터당 천 킬로미터"),
        ("1,000m/L", "리터당 천 미터"),
        ("1,000 m/L", "리터당 천 미터"),
    ],
)
def test_phase36b_valid_comma_compound_units(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("환율은 1,330원 근처입니다.", "환율은 천삼백삼십 원 근처입니다."),
        (
            "상담 건수는 1,200건이고 예약자는 8,500명입니다.",
            "상담 건수는 천이백 건이고 예약자는 팔천오백 명입니다.",
        ),
        (
            "고도는 1,250 m이고 속도는 1,000 km/h입니다.",
            "고도는 천이백오십 미터이고 속도는 시속 천 킬로미터입니다.",
        ),
        (
            "주파수는 1,000 Hz이고 로그는 1,000 MB입니다.",
            "주파수는 천 헤르츠이고 로그는 천 메가바이트입니다.",
        ),
    ],
)
def test_phase36b_embedded_korean_sentences(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "1,25m",
        "12,34kg",
        "1,23,456원",
        "1,,000m",
        "1,000,km/h",
        "1,000mtest",
        "1,000 mtest",
        "1,000km/hour",
        "1,000 km/hour",
    ],
)
def test_phase36b_invalid_comma_and_unsafe_tail_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "abc1,250m",
        "A1,250 m",
        "model25 ℃",
        "25 ℃abc",
        "1,250 mtest",
        "8.5 m/minute",
        "250 m/Lite",
    ],
)
def test_phase36b_identifier_boundary_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "1,000 km / h",
        "8.5 m / min",
    ],
)
def test_phase36b_slash_space_non_goal_preserve(text: str) -> None:
    assert transform(text) == text
