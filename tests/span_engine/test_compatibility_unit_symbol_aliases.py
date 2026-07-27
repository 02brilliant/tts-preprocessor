from __future__ import annotations

import pytest

from engine.span_engine.compound_unit import COMPOUND_SLASH_UNIT_READINGS
from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import SPECIAL_UNIT_READINGS


@pytest.mark.parametrize(
    ("symbol_source", "ascii_source", "expected"),
    [
        ("55㎜", "55mm", "오십오 밀리미터"),
        ("55㎝", "55cm", "오십오 센티미터"),
        ("55㎞", "55km", "오십오 킬로미터"),
        ("55㎎", "55mg", "오십오 밀리그램"),
        ("55㎏", "55kg", "오십오 킬로그램"),
        ("55㎖", "55ml", "오십오 밀리리터"),
        ("55ℓ", "55L", "오십오 리터"),
        ("55㎅", "55KB", "오십오 킬로바이트"),
        ("55㎆", "55MB", "오십오 메가바이트"),
        ("55㎇", "55GB", "오십오 기가바이트"),
        ("55㎐", "55Hz", "오십오 헤르츠"),
        ("55㎑", "55kHz", "오십오 킬로헤르츠"),
        ("55㎒", "55MHz", "오십오 메가헤르츠"),
        ("55㎓", "55GHz", "오십오 기가헤르츠"),
        ("55㏈", "55dB", "오십오 데시벨"),
        ("55㎫", "55MPa", "오십오 메가파스칼"),
        ("55㎷", "55mV", "오십오 밀리볼트"),
        ("55㎹", "55MV", "오십오 메가볼트"),
        ("55㎽", "55mW", "오십오 밀리와트"),
        ("55㎾", "55kW", "오십오 킬로와트"),
        ("55㎿", "55MW", "오십오 메가와트"),
        ("55㎧", "55m/s", "초속 오십오 미터"),
    ],
)
def test_compatibility_symbol_matches_registered_ascii_unit(
    symbol_source: str, ascii_source: str, expected: str
) -> None:
    assert transform(symbol_source) == expected
    assert transform(symbol_source) == transform(ascii_source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2.5㎿", "이쩜오 메가와트"),
        ("2.5 ㎾", "이쩜오 킬로와트"),
        ("2.5㎑", "이쩜오 킬로헤르츠"),
        ("2.5㎆", "이쩜오 메가바이트"),
        ("2.5㎽", "이쩜오 밀리와트"),
        ("2.5㎷", "이쩜오 밀리볼트"),
        ("2.5㎹", "이쩜오 메가볼트"),
        ("2.5㎫", "이쩜오 메가파스칼"),
        ("2.5ℓ", "이쩜오 리터"),
        ("2.5㎧", "초속 이쩜오 미터"),
        ("45m2", "사십오 제곱미터"),
        ("45cm2", "사십오 제곱센티미터"),
        ("45km2", "사십오 제곱킬로미터"),
        ("55‰", "오십오 퍼밀"),
    ],
)
def test_compatibility_and_policy_area_units_accept_registered_numeric_forms(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "㎿",
        "55㎿abc",
        "55㎆abc",
        "55㎧abc",
        "55㎙",
        "55㎩",
        "`55㎿`",
        '{"power":"55㎿"}',
        "https://example.com/55㎿",
    ],
)
def test_unregistered_or_unsafe_compatibility_symbols_preserve(source: str) -> None:
    assert transform(source) == source


def test_compatibility_alias_registries_are_policy_aligned() -> None:
    assert {
        "ℓ": "리터",
        "㎅": "킬로바이트",
        "㎆": "메가바이트",
        "㎇": "기가바이트",
        "㎑": "킬로헤르츠",
        "㎫": "메가파스칼",
        "㎷": "밀리볼트",
        "㎹": "메가볼트",
        "㎽": "밀리와트",
        "㎾": "킬로와트",
        "㎿": "메가와트",
        "‰": "퍼밀",
    }.items() <= SPECIAL_UNIT_READINGS.items()
    assert COMPOUND_SLASH_UNIT_READINGS["㎧"] == "초속 {number} 미터"


def test_megawatt_symbol_is_claimed_by_special_unit_owner() -> None:
    output = transform_with_trace("55㎿")

    assert output.normalized_text == "오십오 메가와트"
    assert output.trace is not None
    assert any(log.owner == "special_unit" for log in output.trace.claim_logs)
