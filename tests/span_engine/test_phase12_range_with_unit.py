from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3~8cm", "삼에서 팔-센티미터"),
        ("1~5kg", "일에서 오-킬로그램"),
        ("10~20%", "십에서 이십-퍼센트"),
        ("3∼8cm", "삼에서 팔-센티미터"),
        ("45~50㎡", "사십오에서 오십-제곱미터"),
        ("1~3㎏", "일에서 삼-킬로그램"),
        ("길이는 3~8cm입니다", "길이는 삼에서 팔-센티미터입니다"),
        ("비율은 10~20%는 가능", "비율은 십에서 이십-퍼센트는 가능"),
        ("무게는 1~5kg을 허용", "무게는 일에서 오-킬로그램을 허용"),
        ("길이는 3~8cm를 측정", "길이는 삼에서 팔-센티미터를 측정"),
        ("45~50만kg", "사십오에서 오십만-킬로그램"),
        ("45~50만 kg", "사십오에서 오십만-킬로그램"),
        ("45~50만㎡", "사십오에서 오십만-제곱미터"),
        ("3~8만kg", "삼에서 팔만-킬로그램"),
        ('3.5~8만kg', '삼-쩜-오에서 팔만-킬로그램'),
        ("1억~2억kg", "일억에서 이억-킬로그램"),
        ("1만~2만km", "일만에서 이만-킬로미터"),
        ('3.5만~8만kg', '삼-쩜-오-만에서 팔만-킬로그램'),
        ("무게는 45~50만kg입니다", "무게는 사십오에서 오십만-킬로그램입니다"),
    ],
)
def test_range_with_unit(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ('3~8cm', '삼에서 팔cm'),
        ('3~8cm', '삼~팔 센티미터'),
        ('3~8cm', '3~팔 센티미터'),
        ('3~8cm', '삼에서 팔cm'),
        ('45~50만kg', '45~50만 킬로그램'),
        ('45~50만kg', '45~50만 킬로그램'),
    ],
)
def test_range_with_unit_forbidden_partial_outputs(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
