from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90km/h", "시속 구십 킬로미터"),
        ("15km/L", "리터당 십오 킬로미터"),
        ("3m/s", "초속 삼 미터"),
        ("100MB/s", "초당 백 메가바이트"),
        ("5GB/s", "초당 오 기가바이트"),
        ("120mg/dL", "데시리터당 백이십 밀리그램"),
        ("2g/L", "리터당 이 그램"),
        ("속도는 90km/h입니다", "속도는 시속 구십 킬로미터입니다"),
        ("연비는 15km/L입니다", "연비는 리터당 십오 킬로미터입니다"),
        ("전송률은 100MB/s까지", "전송률은 초당 백 메가바이트까지"),
        ("혈당은 120mg/dL입니다", "혈당은 데시리터당 백이십 밀리그램입니다"),
        ('15.2km/L', '리터당 십오쩜이 킬로미터'),
    ],
)
def test_compound_slash_unit_basic_expected_output(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90km/h은 빠르다", "시속 구십 킬로미터는 빠르다"),
        ("90km/h는 빠르다", "시속 구십 킬로미터는 빠르다"),
        ("120mg/dL을 넘다", "데시리터당 백이십 밀리그램을 넘다"),
        ("120mg/dL를 넘다", "데시리터당 백이십 밀리그램을 넘다"),
        ("90km/h로 이동", "시속 구십 킬로미터로 이동"),
    ],
)
def test_compound_slash_unit_safe_particle_interaction(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
