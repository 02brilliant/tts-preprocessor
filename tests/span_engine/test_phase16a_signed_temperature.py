from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-2℃", "영하 이도"),
        ("+2℃", "영상 이도"),
        ("-2.5℃", "영하 이쩜오도"),
        ("+3.5℃", "영상 삼쩜오도"),
        ("온도는 -2.5℃입니다", "온도는 영하 이쩜오도입니다"),
        ("기온은 +3℃까지", "기온은 영상 삼도까지"),
    ],
)
def test_signed_temperature_expected_output(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("-2℃은 낮다", "영하 이도는 낮다"),
        ("-2℃는 낮다", "영하 이도는 낮다"),
        ("-2℃로 설정", "영하 이도로 설정"),
    ],
)
def test_signed_temperature_safe_particle_interaction(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
