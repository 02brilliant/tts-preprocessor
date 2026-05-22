from __future__ import annotations

from engine.span_engine import transform


def test_phase33c_superscript_area_volume_units_full_consume() -> None:
    assert transform("45m²") == "사십오 제곱미터"
    assert transform("45m³") == "사십오 세제곱미터"
    assert transform("45cm²") == "사십오 제곱센티미터"
    assert transform("45cm³") == "사십오 세제곱센티미터"
    assert transform("45km²") == "사십오 제곱킬로미터"
    assert transform("45㎡") == "사십오 제곱미터"
    assert transform("45㎥") == "사십오 세제곱미터"


def test_phase33c_superscript_area_volume_units_in_sentence() -> None:
    assert transform("면적은 45m²이다") == "면적은 사십오 제곱미터이다"
    assert transform("부피는 45m³이다") == "부피는 사십오 세제곱미터이다"


def test_phase33c_superscript_unit_unsafe_tail_preserved() -> None:
    assert transform("45m²abc") == "45m²abc"
    assert transform("45m³abc") == "45m³abc"


def test_phase33c_unsupported_superscript_tokens_preserved() -> None:
    assert transform("x²") == "x²"
    assert transform("A²B") == "A²B"
