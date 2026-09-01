from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("10Mbps", "십 메가비피에스"),
        ("10 Mbps", "십 메가비피에스"),
        ("10Kbps", "십 킬로비피에스"),
        ("10 Kbps", "십 킬로비피에스"),
        ("10Gbps", "십 기가비피에스"),
        ("10 Gbps", "십 기가비피에스"),
        ("10Tbps", "십 테라비피에스"),
        ("10 Tbps", "십 테라비피에스"),
        ("10bps", "십 비피에스"),
        ("10 bps", "십 비피에스"),
        ("60fps", "육십 에프피에스"),
        ("60 fps", "육십 에프피에스"),
        ("10rpm", "십 알피엠"),
        ("10 rpm", "십 알피엠"),
        ("10ppm", "십 피피엠"),
        ("10 ppm", "십 피피엠"),
        ("10ppb", "십 피피비"),
        ("10 ppb", "십 피피비"),
        ("9dBi", "구 디비아이"),
        ("9 dBi", "구 디비아이"),
        ('2.35 Mbps', '이-쩜-삼오 메가비피에스'),
        ("1,000 Mbps", "천 메가비피에스"),
        ("+10Mbps", "플러스 십 메가비피에스"),
        ("+10 Mbps", "플러스 십 메가비피에스"),
        ("-10Mbps", "마이너스 십 메가비피에스"),
        ("-10 Mbps", "마이너스 십 메가비피에스"),
        ("−10Mbps", "마이너스 십 메가비피에스"),
        ("제10Mbps", "제십 메가비피에스"),
        ("제10 Mbps", "제십 메가비피에스"),
        ("제 10 Mbps", "제 십 메가비피에스"),
        ("10~20Mbps", "십에서 이십-메가비피에스"),
        ("10~20 Mbps", "십에서 이십-메가비피에스"),
        ("10-20Mbps", "십에서 이십-메가비피에스"),
        ("10-20 Mbps", "십에서 이십-메가비피에스"),
        ("3만Mbps", "삼만-메가비피에스"),
        ("3만 Mbps", "삼만-메가비피에스"),
        ("속도는 10 Mbps입니다", "속도는 십 메가비피에스입니다"),
    ],
)
def test_exact_compound_units_read_attached_and_one_ascii_space(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "10 in",
        "10 km / h",
        "10 m / s",
        "10 MB / s",
        "+-10Mbps",
        "1/2Mbps",
        "10Mbpsabc",
        "10  Mbps",
    ],
)
def test_inch_slash_internal_and_unsafe_exact_compound_forms_preserve(
    source: str,
) -> None:
    assert transform(source) == source


def test_spaced_mbps_uses_compound_exact_owner() -> None:
    output = transform_with_trace("10 Mbps")
    assert output.normalized_text == "십 메가비피에스"
    assert any(
        claim.owner == "compound_exact_unit"
        and claim.reason == "compound_exact_unit_inventory_match"
        for claim in output.trace.claim_logs
    )
