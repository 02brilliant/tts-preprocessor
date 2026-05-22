from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90km/hr", "시속 구십 킬로미터"),
        ("90㎞/h", "시속 구십 킬로미터"),
        ("3m/s", "초속 삼 미터"),
        ("3m/sec", "초속 삼 미터"),
        ("120mg/L", "리터당 백이십 밀리그램"),
        ("2g/L", "리터당 이 그램"),
        ("10KB/s", "초당 십 킬로바이트"),
        ("100MB/s", "초당 백 메가바이트"),
        ("5GB/s", "초당 오 기가바이트"),
        ("속도는 90km/hr입니다", "속도는 시속 구십 킬로미터입니다"),
        ("속도는 90㎞/h입니다", "속도는 시속 구십 킬로미터입니다"),
        ("속도는 3m/s입니다", "속도는 초속 삼 미터입니다"),
        ("혈액은 120mg/L입니다", "혈액은 리터당 백이십 밀리그램입니다"),
        ("전송률은 10KB/s입니다", "전송률은 초당 십 킬로바이트입니다"),
        ("전송률은 100MB/s입니다", "전송률은 초당 백 메가바이트입니다"),
        ("전송률은 5GB/s입니다", "전송률은 초당 오 기가바이트입니다"),
    ],
)
def test_phase17b_policy_inventory_slash_units(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3000rpm", "삼천 알피엠"),
        ("60fps", "육십 에프피에스"),
        ("10Mbps", "십 메가비피에스"),
        ("2Gbps", "이 기가비피에스"),
        ("7ppm", "칠 피피엠"),
        ("8ppb", "팔 피피비"),
        ("9dBi", "구 디비아이"),
        ("속도는 3000rpm입니다", "속도는 삼천 알피엠입니다"),
        ("화질은 60fps입니다", "화질은 육십 에프피에스입니다"),
        ("속도는 10Mbps입니다", "속도는 십 메가비피에스입니다"),
        ("출력은 9dBi입니다", "출력은 구 디비아이입니다"),
    ],
)
def test_phase17b_policy_inventory_exact_compound_units(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
