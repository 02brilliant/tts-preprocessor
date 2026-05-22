from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3~8cm", "삼에서 팔 센티미터"),
        ("1~5kg", "일에서 오 킬로그램"),
        ("10~20%", "십에서 이십 퍼센트"),
        ("3∼8cm", "삼에서 팔 센티미터"),
        ("45~50㎡", "사십오에서 오십 제곱미터"),
        ("1~3㎏", "일에서 삼 킬로그램"),
        ("길이는 3~8cm입니다", "길이는 삼에서 팔 센티미터입니다"),
        ("비율은 10~20%는 가능", "비율은 십에서 이십 퍼센트는 가능"),
        ("무게는 1~5kg을 허용", "무게는 일에서 오 킬로그램을 허용"),
        ("길이는 3~8cm를 측정", "길이는 삼에서 팔 센티미터를 측정"),
    ],
)
def test_range_with_unit(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("3~8cm", "삼~팔 센티미터"),
        ("3~8cm", "삼~8cm"),
        ("3~8cm", "3~팔 센티미터"),
        ("3~8cm", "삼에서 팔cm"),
    ],
)
def test_range_with_unit_forbidden_partial_outputs(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
