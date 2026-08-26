from __future__ import annotations

import pytest

from engine.span_engine import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("60fps은 낮다", "육십 에프피에스는 낮다"),
        ("60fps는 낮다", "육십 에프피에스는 낮다"),
        ("3000rpm은 높다", "삼천 알피엠은 높다"),
        ("3000rpm는 높다", "삼천 알피엠은 높다"),
        ("10bps를 지원", "십 비피에스를 지원"),
        ("10 bps를 지원", "십 비피에스를 지원"),
        ("10Mbps를 지원", "십 메가비피에스를 지원"),
        ("10Mbps을 지원", "십 메가비피에스를 지원"),
        ("9dBi로 설정", "구 디비아이로 설정"),
    ],
)
def test_phase17b_exact_compound_safe_particle(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["10bps", "10 bps"])
def test_bps_uses_compound_exact_unit_owner(text: str) -> None:
    output = transform_with_trace(text)
    assert output.normalized_text == "십 비피에스"
    assert any(
        claim.owner == "compound_exact_unit"
        and claim.reason == "compound_exact_unit_inventory_match"
        for claim in output.trace.claim_logs
    )
