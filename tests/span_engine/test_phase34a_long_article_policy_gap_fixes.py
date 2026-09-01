from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25℃", "이십오도"),
        ("25º", "이십오도"),
        ("25ºC", "이십오도"),
        ('2.5℃', '이-쩜-오도'),
        ('2.5º', '이-쩜-오도'),
        ('2.5ºC', '이-쩜-오도'),
        ("25℉", "화씨 이십오도"),
        ("25ºF", "화씨 이십오도"),
        ('2.5℉', '화씨 이-쩜-오도'),
        ('2.5ºF', '화씨 이-쩜-오도'),
        ('-2.5℃', '영하 이-쩜-오도'),
        ('-2.5ºC', '영하 이-쩜-오도'),
        ('-2.5℉', '화씨 영하 이-쩜-오도'),
        ('-2.5ºF', '화씨 영하 이-쩜-오도'),
    ],
)
def test_phase34a_unsigned_and_signed_temperature_units(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["30ºCtest", "40℉abc", "2.5ºFahrenheit"],
)
def test_phase34a_temperature_unsafe_tail_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("7시간 05분", "일곱-시간 오분"),
        ("2시간 32분", "두-시간 삼십이분"),
        ("3시간 이상", "세-시간 이상"),
        ("3시간 18분", "세-시간 십팔분"),
    ],
)
def test_phase34a_duration_time_units(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15건", "열다섯-건"),
        ("59건", "오십구-건"),
        ("120점", "백이십-점"),
        ("8곳", "여덟-곳"),
    ],
)
def test_phase34a_counter_inventory_expansion(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('$25.99', '이십오-쩜-구구-달러'),
        ("€1,234", "천이백삼십사-유로"),
        ('1,234.56 EUR', '천이백삼십사-쩜-오육-유로'),
        ('1,234.56€', '천이백삼십사-쩜-오육-유로'),
        ("300 USD", "삼백-달러"),
        ("300 EUR", "삼백-유로"),
        ("300 KRW", "삼백-원"),
        ("₩12,300", "만 이천삼백-원"),
        ("￥1,500", "천오백-엔"),
        ('€1,234.56', '천이백삼십사-쩜-오육-유로'),
        ("$300", "삼백-달러"),
        ("￦300", "삼백-원"),
    ],
)
def test_phase34a_currency_decimal_and_code_coverage(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "EURA 300",
        "300EURabc",
        "USDX 300",
        "300KRWa",
        "USB300",
        "KRWabc",
        "€abc",
        "$abc",
    ],
)
def test_phase34a_currency_code_like_unsafe_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('12.5MB', '십이-쩜-오-메가바이트'),
        ('3.2GB', '삼-쩜-이-기가바이트'),
        ("8GB", "팔-기가바이트"),
        ('2.4PB', '이-쩜-사-페타바이트'),
        ('3.2kWh', '삼-쩜-이-킬로와트시'),
        ("1Gbps", "일 기가비피에스"),
    ],
)
def test_phase34a_data_and_power_unit_coverage(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["12.5MBabc", "3.2GBtest", "2.4PBx", "3.2kWhabc"],
)
def test_phase34a_data_unit_unsafe_tail_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("60Hz", "육십-헤르츠"),
        ("60hz", "육십-헤르츠"),
        ('0.5Hz', '영-쩜-오-헤르츠'),
        ('0.5hz', '영-쩜-오-헤르츠'),
        ("120 Hz", "백이십-헤르츠"),
        ("120 hz", "백이십-헤르츠"),
        ('3.2MHz', '삼-쩜-이-메가헤르츠'),
        ('3.2GHz', '삼-쩜-이-기가헤르츠'),
        ("5Hz급", "오-헤르츠급"),
        ("5hz급", "오-헤르츠급"),
    ],
)
def test_phase34a_frequency_unit_coverage(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["5Hzabc", "5hzabc", "Hz", "hz"])
def test_phase34a_frequency_unsafe_or_standalone_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('pH 7.4', '피에이치 칠-쩜-사'),
        ('pH7.4', '피에이치 칠-쩜-사'),
        ("pH 12", "피에이치 십이"),
        ("pH12", "피에이치 십이"),
        ('pH 0.5', '피에이치 영-쩜-오'),
        ('pH0.5', '피에이치 영-쩜-오'),
        ("pH 7", "피에이치 칠"),
        ("pH7", "피에이치 칠"),
        ('pH 10.25', '피에이치 십-쩜-이오'),
    ],
)
def test_phase34a_ph_normalization(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    ["xpH 7.4", "apH7.4", "pH 7.4a", "pH7.4test", "pH"],
)
def test_phase34a_ph_unsafe_or_standalone_preserve(text: str) -> None:
    assert transform(text) == text


def test_phase34a_ph_suffix_position_current_policy_retained() -> None:
    assert transform("7.4 pH") == '칠-쩜-사 pH'


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12 · 3", "십이 · 삼"),
        ("12. 3", "12. 3"),
        ("12 .3", "12 .3"),
    ],
)
def test_phase34a_spaced_separator_policy(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("12·3 비상계엄", "십이삼 비상계엄"),
        ('3.14', '삼-쩜-일사'),
        ("7·25", "칠·이오"),
        ("10·5", "일영·오"),
    ],
)
def test_phase34a_separator_normal_cases_retained(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4위", "사-위"),
        ("1∼11월", "일월에서 십일월"),
        ("2:1", "이 대 일"),
        ("(-3)", ""),
    ],
)
def test_phase34a_remaining_explicit_non_goals_current_behavior_retained(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
