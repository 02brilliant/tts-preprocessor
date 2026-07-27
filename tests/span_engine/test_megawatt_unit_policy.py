from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import SIMPLE_UNIT_READINGS


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1W", "일 와트"),
        ("1 kW", "일 킬로와트"),
        ("2MW", "이 메가와트"),
        ("2.5 MW", "이쩜오 메가와트"),
        ("1,000.50MW", "천쩜오영 메가와트"),
        ("+2.5MW", "플러스 이쩜오 메가와트"),
        ("-2.5 MW", "마이너스 이쩜오 메가와트"),
        ("1Wh", "일 와트시"),
        ("2kWh", "이 킬로와트시"),
        ("3MWh", "삼 메가와트시"),
        ("3.2 MWh", "삼쩜이 메가와트시"),
        ("3MW급", "삼 메가와트급"),
    ],
)
def test_registered_power_units_use_numeric_prefix_reading(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(log.owner == "simple_unit" for log in output.trace.claim_logs)


@pytest.mark.parametrize(
    "source",
    [
        "3MWabc",
        "3MWhabc",
        "3MW/h",
        "1KW",
        "1mW",
        "1GW",
        "1MV",
        "1MA",
        "1MJ",
        "1MPa",
        "1Mm",
        "1Mg",
        "MW",
    ],
)
def test_unregistered_or_unsafe_power_like_surfaces_preserve(source: str) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1MHz", "일 메가헤르츠"),
        ("1MB", "일 메가바이트"),
        ("1Mbps", "일 메가비피에스"),
        ("1MB/s", "초당 일 메가바이트"),
        ("1ML", "일 밀리리터"),
    ],
)
def test_existing_safe_m_prefixed_readings_and_ml_alias_remain_stable(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_power_unit_registry_is_longest_match_and_policy_aligned() -> None:
    assert {
        "W": "와트",
        "kW": "킬로와트",
        "MW": "메가와트",
        "Wh": "와트시",
        "kWh": "킬로와트시",
        "MWh": "메가와트시",
    }.items() <= SIMPLE_UNIT_READINGS.items()
