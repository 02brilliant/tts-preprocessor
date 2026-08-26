from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace
from engine.span_engine.compound_unit import COMPOUND_EXACT_UNIT_READINGS
from engine.span_engine.units import (
    HANGUL_CONTEXT_UNIT_EXCLUSIONS,
    SIMPLE_UNIT_READINGS,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("10bp", "십 베이시스 포인트"),
        ("10BP", "십 베이시스 포인트"),
        ("10 bp", "십 베이시스 포인트"),
        ("10 BP", "십 베이시스 포인트"),
        ("2.5bp", "이쩜오 베이시스 포인트"),
        ("1,000bp", "천 베이시스 포인트"),
        ("+2.5bp", "플러스 이쩜오 베이시스 포인트"),
        ("-15BP", "마이너스 십오 베이시스 포인트"),
        ("–2.5bp", "마이너스 이쩜오 베이시스 포인트"),
        ("3만bp", "삼만 베이시스 포인트"),
        ("3만 bp", "삼만 베이시스 포인트"),
        ("3.5만bp", "삼쩜오 만 베이시스 포인트"),
        ("45~50만bp", "사십오에서 오십만 베이시스 포인트"),
        ("3~5bp", "삼에서 오 베이시스 포인트"),
        ("금리는 25bp 올랐다", "금리는 이십오 베이시스 포인트 올랐다"),
    ],
)
def test_registered_basis_point_reads_like_other_latin_units(
    source: str, expected: str
) -> None:
    output = transform_with_trace(source)

    assert output.normalized_text == expected
    assert output.trace is not None
    assert any(
        log.owner
        in {
            "simple_unit",
            "korean_numeric_unit",
            "range_with_unit",
        }
        for log in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("10Bp", "10Bp"),
        ("bp", "bp"),
        ("BP", "비피"),
        ("10bpabc", "10bpabc"),
        ("1/2bp", "1/2bp"),
        ("수 bp", "수 bp"),
        ("수 BP", "수 비피"),
    ],
)
def test_basis_point_keeps_rate_collision_and_hangul_context_guards(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


def test_basis_point_registry_and_hangul_context_policy() -> None:
    assert {"bp": "베이시스 포인트", "BP": "베이시스 포인트"}.items() <= (
        SIMPLE_UNIT_READINGS.items()
    )
    assert {"bp", "BP"} <= HANGUL_CONTEXT_UNIT_EXCLUSIONS
    assert "bps" not in SIMPLE_UNIT_READINGS
    assert "Bps" not in SIMPLE_UNIT_READINGS
    assert COMPOUND_EXACT_UNIT_READINGS["bps"] == "{number} 비피에스"


def test_attached_basis_point_uses_simple_unit_owner() -> None:
    output = transform_with_trace("10bp")
    assert any(
        claim.owner == "simple_unit" and claim.reason == "simple_unit_numeric_prefix"
        for claim in output.trace.claim_logs
    )
