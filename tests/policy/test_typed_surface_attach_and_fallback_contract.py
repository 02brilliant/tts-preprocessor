from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.models import SourceSpan, Surface
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1대1로", "일대일로"),
        ("60여 명이", "육십여 명이"),
        ("1만3천여 명을", "일만삼천여 명을"),
        ("제62회는", "제-육십이회는"),
        ("MFN율은", "엠에프엔율은"),
        ("AI기반은", "에이아이기반은"),
        ("3~8cm는", "삼에서 팔-센티미터는"),
        ("1∼11월은", "일월에서 십일월은"),
    ],
)
def test_particle_attaches_after_owned_span_surface(text: str, expected: str):
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert output.trace.claim_logs
    assert any(
        claim.claim_type == "surface"
        for claim in output.trace.claim_logs
    )
    assert any(
        piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )


def test_span_surface_model_rejects_particle_span_without_particle():
    with pytest.raises(ValueError):
        Surface(
            surface_type="TEST_SURFACE",
            owner="test",
            raw="1",
            span=SourceSpan(0, 1),
            reading="일",
            trailing_particle_span=SourceSpan(1, 2),
        )


def test_non_attachable_span_surface_keeps_particle_outside_claim():
    output = transform_with_trace("K-푸드가")
    assert output.normalized_text == transform("K-푸드가")
    claim = next(
        claim for claim in output.trace.claim_logs
        if claim.owner == "k_hangul_lexical"
    )
    assert claim.claim_type == "surface"
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and piece.owner == claim.owner
        for piece in output.render_pieces
    )
