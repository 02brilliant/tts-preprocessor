from __future__ import annotations

import pytest

from engine.main import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("40번", "사십-번"),
        ("40번 버스", "사십번 버스"),
        ("총 40번 시도했다", "총 사십-번 시도했다"),
        ("3번", "3번"),
        ("301조에", "삼백일-조에"),
        ("3조에", "3조에"),
        ("40조에", "사십-조에"),
        ("예산 40조", "예산 사십조"),
        ("총 40조를 편성했다", "총 사십-조를 편성했다"),
        ("40대", "사십-대"),
        ("39대", "39대"),
        ("5대", "5대"),
        ("40층", "사십-층"),
        ("3층", "3층"),
        ("50호", "오십-호"),
        ("3호", "3호"),
        ("제40조", "제-사십조"),
        ("1조가", "1조가"),
    ],
)
def test_residual_threshold_reads_unresolved_units_without_stealing_confirmed_spacing(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("18분", "18분"),
        ("40분", "40분"),
        ("99분", "99분"),
        ("100분", "백-분"),
        ("0분", "영-분"),
        ("손님 40분이 도착했다", "손님 마흔-분이 도착했다"),
        ("손님 100분이 도착했다", "손님 백-분이 도착했다"),
        ("40가지", "마흔-가지"),
        ("99가지", "아흔아홉-가지"),
        ("100가지", "백-가지"),
        ("0가지", "영-가지"),
        ("4가지", "네-가지"),
    ],
)
def test_bun_and_gaji_keep_one_to_ninety_nine_meaning_split(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3시리즈", "삼-시리즈"),
        ("12시리즈", "십이-시리즈"),
        ("11시스템", "십일 시스템"),
        ("12시장", "십이 시장"),
        ("12시험", "십이 시험"),
        ("12시즌", "십이 시즌"),
        ("낮 12시리즈", "낮 십이-시리즈"),
        ("3시회의", "3시회의"),
        ("99시", "구십구 시"),
        ("25시", "25시"),
        ("40시", "사십 시"),
        ("24시", "이십사-시"),
        ("99시23분45초", "99시23분45초"),
        ("11시점", "11시점"),
        ("3시abc", "3시abc"),
        ("A3시", "A3시"),
    ],
)
def test_undefined_or_invalid_si_surfaces_follow_residual_and_clock_split(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-40분", "마이너스 사십 분"),
        ("+40대", "플러스 사십 대"),
        ("-5가지", "마이너스 오 가지"),
        ("+-3", "플러스 마이너스 삼"),
        ("+-40분", "플러스 마이너스 사십 분"),
        ("+-1.5", "플러스 마이너스 일쩜오"),
        ("±3", "플러스 마이너스 삼"),
        ("±1.5", "플러스 마이너스 일쩜오"),
        ("-+3", "-+3"),
        ("+- 3", "+- 3"),
        ("F-35", "에프-삼십오"),
        ("가-3", "가-삼"),
        ("-3시간", "마이너스 세-시간"),
        ("-18분", "마이너스 십팔 분"),
        ("-3시간 18분", "마이너스 세-시간 십팔분"),
        ("3시간 -18분", "세-시간 마이너스 십팔분"),
        ("3시간-18분", "세-시간-18분"),
    ],
)
def test_signed_integer_residual_and_plus_minus_compound(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.5분", "영쩜오-분"),
        ("40.5분", "사십쩜오-분"),
        ("2.5분", "이쩜오-분"),
        ("1/2점", "이분의 일 점"),
        ("3/4분", "사분의 삼 분"),
        ("1/2분", "이분의 일 분"),
        ("0시리즈", "영-시리즈"),
        ("0조에", "영-조에"),
        ("01분", "01분"),
        ("00층", "00층"),
        ("05분", "05분"),
        ("3A번", "3A번"),
        ("1,00조", "1,00조"),
        ("1,200분", "천이백-분"),
        ("123", "백이십삼"),
        ("010", "010"),
        ("무역법 301조에 따른 관세가 15일 0시부로 부과된다.",
         "무역법 삼백일-조에 따른 관세가 십오일 영-시부로 부과된다."),
    ],
)
def test_decimal_fraction_zero_and_preserve_exceptions(text: str, expected: str) -> None:
    assert transform(text) == expected
