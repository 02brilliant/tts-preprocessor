from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace
from engine.span_engine.particle import choose_safe_particle
from engine.span_engine.units import (
    HANGUL_CONTEXT_UNIT_EXCLUSIONS,
    HANGUL_CONTEXT_UNIT_READINGS,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("연면적 1만㎡ 규모로 조성된다.", "연면적 일만-제곱미터 규모로 조성된다."),
        ("1만㎡", "일만-제곱미터"),
        ("수 km을 달려왔다", "수 킬로미터를 달려왔다"),
        ("수km을 달려왔다", "수 킬로미터를 달려왔다"),
        ("수 km으로", "수 킬로미터로"),
        ("몇 kg", "몇 킬로그램"),
        ("한글 km 한글", "한글 킬로미터 한글"),
        ("연면적 ㎡ 규모로 조성된다.", "연면적 제곱미터 규모로 조성된다."),
        ("kg입니다", "킬로그램입니다"),
        ("km만", "킬로미터만"),
        ("수 Hz", "수 헤르츠"),
        ("수 dB", "수 데시벨"),
        ("수 ℓ", "수 리터"),
        ("수 ㎕", "수 마이크로리터"),
        ("수 ㎗", "수 데시리터"),
        ("수 ㎘", "수 킬로리터"),
        ("수 ㎡", "수 제곱미터"),
        ("수 m²", "수 제곱미터"),
        ("수 GB", "수 기가바이트"),
        ("수 GB을", "수 기가바이트를"),
        ("수GB", "수 기가바이트"),
        ("수 MB", "수 메가바이트"),
        ("수 PB", "수 페타바이트"),
        ("수 MW", "수 메가와트"),
        ("수십 km", "수십-킬로미터"),
        ("3만kg", "삼만-킬로그램"),
        ("3kg을", "삼-킬로그램을"),
        ("10in", "십-인치"),
        ("5ft", "오-피트"),
        ("3min", "삼-분"),
        ("10TB", "십-테라바이트"),
        ("3만TB", "삼만-테라바이트"),
        ("8bit", "팔-비트"),
        ("bit", "비트"),
        ("bit는", "비트는"),
    ],
)
def test_hangul_context_and_numeric_unit_examples(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("unit", "reading"),
    sorted(HANGUL_CONTEXT_UNIT_READINGS.items()),
    ids=[unit for unit, _ in sorted(HANGUL_CONTEXT_UNIT_READINGS.items())],
)
def test_hangul_context_reads_every_enabled_unit(unit: str, reading: str) -> None:
    particle = choose_safe_particle(reading, "을")
    assert transform(f"수 {unit}") == f"수 {reading}"
    assert transform(f"한글 {unit} 한글") == f"한글 {reading} 한글"
    assert transform(f"수 {unit}을") == f"수 {reading}{particle}"
    assert transform(f"수{unit}을") == f"수 {reading}{particle}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("km", "km"),
        ("㎡", "㎡"),
        ("kg", "kg"),
        ("the kg", "the kg"),
        ("a km away", "a km away"),
        ("in kg", "in kg"),
        ("수 m을", "수 m을"),
        ("수 g", "수 g"),
        ("수 L", "수 L"),
        ("수 W", "수 W"),
        ("수 %", "수 %"),
        ("수 ℃", "수 ℃"),
        ("수 m2", "수 m2"),
        ("수 km/h", "수 km/h"),
        ("수 KB", "수 케이비"),
        ("KB금융", "케이비금융"),
        ("수 ML", "수 ML"),
        ("ML모델", "엠엘모델"),
        ("수 MV", "수 엠브이"),
        ("MV공개", "엠브이공개"),
        ("GB는", "지비는"),
        ("GB그룹", "지비그룹"),
        ("MB정부", "엠비정부"),
        ("PB는", "피비는"),
        ("MW그룹", "엠더블유그룹"),
        ("21명kg", "21명kg"),
        ("3가kg", "3가kg"),
        ("21명abc", "21명abc"),
        ("수 in", "수 in"),
        ("수 ft", "수 ft"),
        ("수 min", "수 min"),
        ("10 in", "10 in"),
        ("a bit", "a bit"),
        ("the bit", "the bit"),
        ("in", "in"),
        ("ft", "ft"),
        ("min", "min"),
        ("TB", "TB"),
        ("TB는", "티비는"),
        ("수 um", "수 um"),
        ("수 ug", "수 ug"),
        ("수 pg", "수 pg"),
        ("수 mm2", "수 mm2"),
        ("수 mm3", "수 mm3"),
        ("GW는", "지더블유는"),
        ("TW는", "티더블유는"),
        ("수 us", "수 us"),
        ("수 ps", "수 ps"),
        ("수 secs", "수 secs"),
    ],
)
def test_hangul_context_does_not_steal_unsafe_or_acronym_forms(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_hangul_context_unit_uses_simple_or_special_owner() -> None:
    output = transform_with_trace("수 km을 달려왔다")
    claims = [claim for claim in output.trace.claim_logs if claim.reason == "hangul_context_unit"]
    assert claims
    assert claims[0].owner == "simple_unit"


def test_special_symbol_hangul_context_keeps_special_owner() -> None:
    output = transform_with_trace("수 ㎡")
    claims = [claim for claim in output.trace.claim_logs if claim.reason == "hangul_context_unit"]
    assert claims
    assert claims[0].owner == "special_unit"


def test_excluded_inventory_does_not_include_enabled_units() -> None:
    overlap = set(HANGUL_CONTEXT_UNIT_READINGS) & set(HANGUL_CONTEXT_UNIT_EXCLUSIONS)
    assert not overlap
    assert "km" in HANGUL_CONTEXT_UNIT_READINGS
    assert "㎡" in HANGUL_CONTEXT_UNIT_READINGS
    assert "KB" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "m" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "in" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "ft" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "um" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "pg" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "min" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "us" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "ps" in HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "bit" in HANGUL_CONTEXT_UNIT_READINGS
    assert "TB" in HANGUL_CONTEXT_UNIT_READINGS
    assert "GW" in HANGUL_CONTEXT_UNIT_READINGS
    assert "Pa" in HANGUL_CONTEXT_UNIT_READINGS
    assert "nm" in HANGUL_CONTEXT_UNIT_READINGS
    assert "sec" in HANGUL_CONTEXT_UNIT_READINGS
    assert "ms" in HANGUL_CONTEXT_UNIT_READINGS
