from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("50kg", "오십 킬로그램"),
        ("3cm", "삼 센티미터"),
        ("10Hz", "십 헤르츠"),
        ("45%", "사십오 퍼센트"),
        ("100MB", "백 메가바이트"),
        ("5GB", "오 기가바이트"),
        ("2L", "이 리터"),
        ("250mL", "이백오십 밀리리터"),
        ("7km", "칠 킬로미터"),
        ("무게는 50kg입니다", "무게는 오십 킬로그램입니다"),
        ("길이는 3cm는 된다", "길이는 삼 센티미터는 된다"),
        ("용량은 100MB을 넘는다", "용량은 백 메가바이트를 넘는다"),
        ("속도는 10Hz으로 설정", "속도는 십 헤르츠로 설정"),
    ],
)
def test_simple_unit_owner_minimal_supported_patterns(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
