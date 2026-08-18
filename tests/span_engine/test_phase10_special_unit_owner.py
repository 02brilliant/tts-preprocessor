from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("45㎡", "사십오 제곱미터"),
        ("3㎏", "삼 킬로그램"),
        ("10㎐", "십 헤르츠"),
        ("20％", "이십 퍼센트"),
        ("5℃", "오도"),
        ("3°", "삼도"),
        ("면적은 45㎡입니다", "면적은 사십오 제곱미터입니다"),
        ("1㎕", "일 마이크로리터"),
        ("1㎗", "일 데시리터"),
        ("1㎘", "일 킬로리터"),
        ("1㎕당", "일 마이크로리터당"),
        ("1㎗당", "일 데시리터당"),
        ("3만㎕", "삼만 마이크로리터"),
        ("3만㎗", "삼만 데시리터"),
        ("3만㎘", "삼만 킬로리터"),
        ("1㎛", "일 마이크로미터"),
        ("1㎩", "일 파스칼"),
        ("1㎸", "일 킬로볼트"),
        ("1㎳", "일 밀리초"),
        ("1㎲", "일 마이크로초"),
        ("온도는 5℃는 낮다", "온도는 오도는 낮다"),
    ],
)
def test_special_unit_owner_minimal_supported_patterns(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-2.5℃", "영하 이쩜오도"),
        ("+3℃", "영상 삼도"),
        ("-3°", "마이너스 삼도"),
    ],
)
def test_signed_temperature_and_degree_supported_in_phase16a(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("300만㎡", "삼백만 제곱미터"),
        ("300만 ㎡", "삼백만 제곱미터"),
        ("3만㎡", "삼만 제곱미터"),
        ("5천㎡", "오천 제곱미터"),
        ("1억㎡", "일억 제곱미터"),
        ("300만m²", "삼백만 제곱미터"),
        ("300만m2", "삼백만 제곱미터"),
        ("1억㎥", "일억 세제곱미터"),
        ("5천m2", "오천 제곱미터"),
        ("5천m²", "오천 제곱미터"),
        ("면적은 300만㎡입니다", "면적은 삼백만 제곱미터입니다"),
        ("연면적 1만㎡ 규모로 조성된다.", "연면적 일만 제곱미터 규모로 조성된다."),
    ],
)
def test_korean_large_unit_special_area_volume_units(text: str, expected: str) -> None:
    assert transform(text) == expected
