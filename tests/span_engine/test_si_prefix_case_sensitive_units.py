from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import SIMPLE_UNIT_READINGS


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("55mW", "오십오-밀리와트"),
        ("55MW", "오십오-메가와트"),
        ("55mV", "오십오-밀리볼트"),
        ("55MV", "오십오-메가볼트"),
        ("55mPa", "오십오-밀리파스칼"),
        ("55MPa", "오십오-메가파스칼"),
        ("55mHz", "오십오-밀리헤르츠"),
        ("55MHz", "오십오-메가헤르츠"),
        ("55mWh", "오십오-밀리와트시"),
        ("55MWh", "오십오-메가와트시"),
        ("55kV", "오십오-킬로볼트"),
        ("55Pa", "오십오-파스칼"),
        ("55GPa", "오십오-기가파스칼"),
        ("2.5 mW", "이쩜오-밀리와트"),
        ("2.5 MV", "이쩜오-메가볼트"),
        ("1,000.50mPa", "천쩜오영-밀리파스칼"),
        ("+2.5MPa", "플러스 이쩜오-메가파스칼"),
        ("-2.5 mV", "마이너스 이쩜오-밀리볼트"),
    ],
)
def test_milli_and_mega_prefixes_are_case_sensitive(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(log.owner == "simple_unit" for log in output.trace.claim_logs)


@pytest.mark.parametrize(
    "source",
    [
        "55mWabc",
        "55MVabc",
        "55mPaabc",
        "55MPabc",
        "55mHzabc",
        "55MW/h",
        "55MPA",
        "55GPA",
        "55KV",
    ],
)
def test_case_sensitive_unit_unsafe_or_excluded_forms_preserve(source: str) -> None:
    assert transform(source) == source


def test_uppercase_mpa_remains_available_to_non_unit_news_rules() -> None:
    standalone = transform_with_trace("MPA")
    attached = transform_with_trace("55MPA")

    assert standalone.normalized_text == "엠피에이"
    assert attached.normalized_text == "55MPA"
    assert standalone.trace is not None
    assert attached.trace is not None
    assert not any(
        log.owner in {"simple_unit", "special_unit"}
        for output in (standalone, attached)
        for log in output.trace.claim_logs
    )
    assert transform("뉴스 약어 MPA입니다") == "뉴스 약어 엠피에이입니다"
    assert transform("압력은 55MPA입니다") == "압력은 55MPA입니다"


def test_case_sensitive_unit_registry_is_policy_aligned() -> None:
    assert {
        "mW": "밀리와트",
        "MW": "메가와트",
        "mV": "밀리볼트",
        "MV": "메가볼트",
        "mPa": "밀리파스칼",
        "MPa": "메가파스칼",
        "mHz": "밀리헤르츠",
        "MHz": "메가헤르츠",
        "mWh": "밀리와트시",
        "MWh": "메가와트시",
        "kV": "킬로볼트",
        "Pa": "파스칼",
        "GPa": "기가파스칼",
    }.items() <= SIMPLE_UNIT_READINGS.items()
    assert "KV" not in SIMPLE_UNIT_READINGS
    assert "GPA" not in SIMPLE_UNIT_READINGS
