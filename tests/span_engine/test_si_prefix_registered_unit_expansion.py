from __future__ import annotations

import pytest

from engine.span_engine.compound_unit import COMPOUND_EXACT_UNIT_READINGS
from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import (
    HANGUL_CONTEXT_UNIT_EXCLUSIONS,
    SIMPLE_UNIT_READINGS,
    SPECIAL_UNIT_READINGS,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("5µm", "오 마이크로미터"),
        ("5μm", "오 마이크로미터"),
        ("5um", "오 마이크로미터"),
        ("5㎛", "오 마이크로미터"),
        ("5nm", "오 나노미터"),
        ("5㎚", "오 나노미터"),
        ("5mm²", "오 제곱밀리미터"),
        ("5mm2", "오 제곱밀리미터"),
        ("5㎟", "오 제곱밀리미터"),
        ("5mm³", "오 세제곱밀리미터"),
        ("5mm3", "오 세제곱밀리미터"),
        ("5㎣", "오 세제곱밀리미터"),
        ("5µg", "오 마이크로그램"),
        ("5μg", "오 마이크로그램"),
        ("5ug", "오 마이크로그램"),
        ("5㎍", "오 마이크로그램"),
        ("5ng", "오 나노그램"),
        ("5pg", "오 피코그램"),
        ("5uL", "오 마이크로리터"),
        ("5nL", "오 나노리터"),
        ("5pL", "오 피코리터"),
        ("5THz", "오 테라헤르츠"),
        ("5Thz", "오 테라헤르츠"),
        ("5thz", "오 테라헤르츠"),
        ("5㎔", "오 테라헤르츠"),
        ("5KHz", "오 킬로헤르츠"),
        ("5khz", "오 킬로헤르츠"),
        ("5Mhz", "오 메가헤르츠"),
        ("5mhz", "오 메가헤르츠"),
        ("5kV", "오 킬로볼트"),
        ("5kv", "오 킬로볼트"),
        ("5㎸", "오 킬로볼트"),
        ("5µV", "오 마이크로볼트"),
        ("5μV", "오 마이크로볼트"),
        ("5uV", "오 마이크로볼트"),
        ("5㎶", "오 마이크로볼트"),
        ("5nV", "오 나노볼트"),
        ("5㎵", "오 나노볼트"),
        ("5Pa", "오 파스칼"),
        ("5㎩", "오 파스칼"),
        ("5kPa", "오 킬로파스칼"),
        ("5㎪", "오 킬로파스칼"),
        ("1013hPa", "천십삼 헥토파스칼"),
        ("5GPa", "오 기가파스칼"),
        ("5µW", "오 마이크로와트"),
        ("5μW", "오 마이크로와트"),
        ("5uW", "오 마이크로와트"),
        ("5㎼", "오 마이크로와트"),
        ("5kw", "오 킬로와트"),
        ("5GW", "오 기가와트"),
        ("5TW", "오 테라와트"),
        ("5mWh", "오 밀리와트시"),
        ("5GWh", "오 기가와트시"),
        ("5TWh", "오 테라와트시"),
        ("2.5µm", "이쩜오 마이크로미터"),
        ("1,013hPa", "천십삼 헥토파스칼"),
        ("3만nm", "삼만 나노미터"),
        ("5bps", "오 비피에스"),
        ("5Kbps", "오 킬로비피에스"),
        ("5kbps", "오 킬로비피에스"),
        ("5mbps", "오 메가비피에스"),
        ("5gbps", "오 기가비피에스"),
        ("5Tbps", "오 테라비피에스"),
        ("5tbps", "오 테라비피에스"),
    ],
)
def test_registered_si_prefix_aliases_read_with_numeric_prefix(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(
        log.owner
        in {
            "simple_unit",
            "special_unit",
            "compound_exact_unit",
            "korean_numeric_unit",
        }
        for log in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    "source",
    [
        "5KV",
        "5KW",
        "5GPA",
        "5NL",
        "5PL",
        "5ul",
        "5NM",
        "5㎙",
        "5㎺",
        "5µma",
        "5GWabc",
        "5nLabc",
        "5Paabc",
    ],
)
def test_unsafe_or_deliberately_unregistered_si_prefix_forms_preserve(
    source: str,
) -> None:
    assert transform(source) == source


def test_picometer_stays_unregistered_and_milliseconds_are_live() -> None:
    assert transform("5pm") != "오 피코미터"
    assert transform("5ms") == "오 밀리초"
    assert transform("5µs") == "오 마이크로초"
    assert transform("5s") == "5s"


def test_picometer_and_bare_second_stay_unregistered() -> None:
    assert "pm" not in SIMPLE_UNIT_READINGS
    assert "s" not in SIMPLE_UNIT_READINGS
    assert "ms" in SIMPLE_UNIT_READINGS
    assert "µs" in SIMPLE_UNIT_READINGS
    assert "KV" not in SIMPLE_UNIT_READINGS
    assert "KW" not in SIMPLE_UNIT_READINGS
    assert "GPA" not in SIMPLE_UNIT_READINGS
    assert "NL" not in SIMPLE_UNIT_READINGS
    assert "PL" not in SIMPLE_UNIT_READINGS
    assert "ul" not in SIMPLE_UNIT_READINGS
    assert "㎙" not in SPECIAL_UNIT_READINGS
    assert "㎺" not in SPECIAL_UNIT_READINGS


def test_hangul_context_excludes_ambiguous_si_alias_tokens() -> None:
    assert {"um", "ug", "pg", "mm2", "mm3", "us", "ps"} <= HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "nm" not in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "Pa" not in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "GW" not in HANGUL_CONTEXT_UNIT_EXCLUSIONS


def test_si_prefix_registry_and_compound_aliases_are_policy_aligned() -> None:
    assert {
        "µm": "마이크로미터",
        "nm": "나노미터",
        "µg": "마이크로그램",
        "ng": "나노그램",
        "pg": "피코그램",
        "uL": "마이크로리터",
        "nL": "나노리터",
        "pL": "피코리터",
        "THz": "테라헤르츠",
        "kV": "킬로볼트",
        "Pa": "파스칼",
        "kPa": "킬로파스칼",
        "hPa": "헥토파스칼",
        "GPa": "기가파스칼",
        "GW": "기가와트",
        "TW": "테라와트",
        "GWh": "기가와트시",
        "TWh": "테라와트시",
        "mWh": "밀리와트시",
    }.items() <= SIMPLE_UNIT_READINGS.items()
    assert {
        "㎛": "마이크로미터",
        "㎚": "나노미터",
        "㎍": "마이크로그램",
        "㎔": "테라헤르츠",
        "㎩": "파스칼",
        "㎪": "킬로파스칼",
        "㎸": "킬로볼트",
        "㎶": "마이크로볼트",
        "㎵": "나노볼트",
        "㎼": "마이크로와트",
        "㎟": "제곱밀리미터",
        "㎣": "세제곱밀리미터",
    }.items() <= SPECIAL_UNIT_READINGS.items()
    assert {
        "bps": "{number} 비피에스",
        "Kbps": "{number} 킬로비피에스",
        "Tbps": "{number} 테라비피에스",
        "mbps": "{number} 메가비피에스",
        "gbps": "{number} 기가비피에스",
    }.items() <= COMPOUND_EXACT_UNIT_READINGS.items()
