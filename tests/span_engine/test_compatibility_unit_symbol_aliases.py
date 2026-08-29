from __future__ import annotations

import pytest

from engine.span_engine.compound_unit import COMPOUND_SLASH_UNIT_READINGS
from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.units import SIMPLE_UNIT_READINGS, SPECIAL_UNIT_READINGS


@pytest.mark.parametrize(
    ("symbol_source", "ascii_source", "expected"),
    [
        ("55㎜", "55mm", "오십오-밀리미터"),
        ("55㎝", "55cm", "오십오-센티미터"),
        ("55㎞", "55km", "오십오-킬로미터"),
        ("55㎎", "55mg", "오십오-밀리그램"),
        ("55㎏", "55kg", "오십오-킬로그램"),
        ("55㎖", "55ml", "오십오-밀리리터"),
        ("55㎕", "55µL", "오십오-마이크로리터"),
        ("55㎕", "55μL", "오십오-마이크로리터"),
        ("55㎗", "55dL", "오십오-데시리터"),
        ("55㎗", "55dl", "오십오-데시리터"),
        ("55㎘", "55kL", "오십오-킬로리터"),
        ("55ℓ", "55L", "오십오-리터"),
        ("55㎅", "55KB", "오십오-킬로바이트"),
        ("55㎆", "55MB", "오십오-메가바이트"),
        ("55㎇", "55GB", "오십오-기가바이트"),
        ("55㎐", "55Hz", "오십오-헤르츠"),
        ("55㎑", "55kHz", "오십오-킬로헤르츠"),
        ("55㎒", "55MHz", "오십오-메가헤르츠"),
        ("55㎓", "55GHz", "오십오-기가헤르츠"),
        ("55㏈", "55dB", "오십오-데시벨"),
        ("55㎫", "55MPa", "오십오-메가파스칼"),
        ("55㎷", "55mV", "오십오-밀리볼트"),
        ("55㎹", "55MV", "오십오-메가볼트"),
        ("55㎽", "55mW", "오십오-밀리와트"),
        ("55㎾", "55kW", "오십오-킬로와트"),
        ("55㎿", "55MW", "오십오-메가와트"),
        ("55㎧", "55m/s", "초속 오십오 미터"),
        ("55㎛", "55µm", "오십오-마이크로미터"),
        ("55㎚", "55nm", "오십오-나노미터"),
        ("55㎍", "55µg", "오십오-마이크로그램"),
        ("55㎔", "55THz", "오십오-테라헤르츠"),
        ("55㎸", "55kV", "오십오-킬로볼트"),
        ("55㎶", "55µV", "오십오-마이크로볼트"),
        ("55㎵", "55nV", "오십오-나노볼트"),
        ("55㎩", "55Pa", "오십오-파스칼"),
        ("55㎪", "55kPa", "오십오-킬로파스칼"),
        ("55㎼", "55µW", "오십오-마이크로와트"),
        ("55㎟", "55mm²", "오십오-제곱밀리미터"),
        ("55㎣", "55mm³", "오십오-세제곱밀리미터"),
        ("55㎳", "55ms", "오십오-밀리초"),
        ("55㎲", "55µs", "오십오-마이크로초"),
        ("55㎱", "55ns", "오십오-나노초"),
        ("55㎰", "55ps", "오십오-피코초"),
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
        ("2.5㎿", "이쩜오-메가와트"),
        ("2.5 ㎾", "이쩜오-킬로와트"),
        ("2.5㎑", "이쩜오-킬로헤르츠"),
        ("2.5㎆", "이쩜오-메가바이트"),
        ("2.5㎽", "이쩜오-밀리와트"),
        ("2.5㎷", "이쩜오-밀리볼트"),
        ("2.5㎹", "이쩜오-메가볼트"),
        ("2.5㎫", "이쩜오-메가파스칼"),
        ("2.5ℓ", "이쩜오-리터"),
        ("2.5㎕", "이쩜오-마이크로리터"),
        ("2.5㎗", "이쩜오-데시리터"),
        ("2.5㎘", "이쩜오-킬로리터"),
        ("2.5㎧", "초속 이쩜오 미터"),
        ("45m2", "사십오-제곱미터"),
        ("45cm2", "사십오-제곱센티미터"),
        ("45km2", "사십오-제곱킬로미터"),
        ("55‰", "오십오-퍼밀"),
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
        "55㎘abc",
        "55㎕abc",
        "55㎗abc",
        "55㎧abc",
        "55㎙",
        "55㎺",
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
        "㎛": "마이크로미터",
        "㎚": "나노미터",
        "㎍": "마이크로그램",
        "㎕": "마이크로리터",
        "㎗": "데시리터",
        "㎘": "킬로리터",
        "㎅": "킬로바이트",
        "㎆": "메가바이트",
        "㎇": "기가바이트",
        "㎑": "킬로헤르츠",
        "㎔": "테라헤르츠",
        "㎩": "파스칼",
        "㎪": "킬로파스칼",
        "㎫": "메가파스칼",
        "㎵": "나노볼트",
        "㎶": "마이크로볼트",
        "㎷": "밀리볼트",
        "㎸": "킬로볼트",
        "㎹": "메가볼트",
        "㎼": "마이크로와트",
        "㎽": "밀리와트",
        "㎾": "킬로와트",
        "㎿": "메가와트",
        "㎟": "제곱밀리미터",
        "㎣": "세제곱밀리미터",
        "㎳": "밀리초",
        "㎲": "마이크로초",
        "㎱": "나노초",
        "㎰": "피코초",
        "‰": "퍼밀",
    }.items() <= SPECIAL_UNIT_READINGS.items()
    assert {
        "µL": "마이크로리터",
        "μL": "마이크로리터",
        "uL": "마이크로리터",
        "nL": "나노리터",
        "pL": "피코리터",
        "dL": "데시리터",
        "dl": "데시리터",
        "kL": "킬로리터",
        "kl": "킬로리터",
        "µm": "마이크로미터",
        "nm": "나노미터",
        "µg": "마이크로그램",
        "kV": "킬로볼트",
        "Pa": "파스칼",
        "hPa": "헥토파스칼",
        "GW": "기가와트",
        "THz": "테라헤르츠",
        "sec": "초",
        "ms": "밀리초",
        "µs": "마이크로초",
    }.items() <= SIMPLE_UNIT_READINGS.items()
    assert "KL" not in SIMPLE_UNIT_READINGS
    assert "DL" not in SIMPLE_UNIT_READINGS
    assert "KW" not in SIMPLE_UNIT_READINGS
    assert "KV" not in SIMPLE_UNIT_READINGS
    assert "pm" not in SIMPLE_UNIT_READINGS
    assert "s" not in SIMPLE_UNIT_READINGS
    assert COMPOUND_SLASH_UNIT_READINGS["㎧"] == "초속 {number} 미터"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1㎕", "일-마이크로리터"),
        ("1㎗", "일-데시리터"),
        ("1㎘", "일-킬로리터"),
        ("1㎛", "일-마이크로미터"),
        ("1㎩", "일-파스칼"),
        ("1㎸", "일-킬로볼트"),
    ],
)
def test_cjk_volume_symbols_are_claimed_by_special_unit_owner(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(log.owner == "special_unit" for log in output.trace.claim_logs)


def test_megawatt_symbol_is_claimed_by_special_unit_owner() -> None:
    output = transform_with_trace("55㎿")

    assert output.normalized_text == "오십오-메가와트"
    assert output.trace is not None
    assert any(log.owner == "special_unit" for log in output.trace.claim_logs)
