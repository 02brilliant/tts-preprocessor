from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("전문가", "전문가"),
        ("있는", "있는"),
        ("전문 가", "전문 가"),
        ("전문  가", "전문  가"),
        ("안녕하세요.", "안녕하세요."),
        ("안녕하세요,", "안녕하세요,"),
        ("안녕하세요 , 반갑습니다", "안녕하세요 , 반갑습니다"),
        ("하지만 , 우리는 간다", "하지만 , 우리는 간다"),
    ],
)
def test_hangul_spacing_and_punctuation_invariance(text: str, expected: str):
    assert transform(text) == expected


@pytest.mark.parametrize("text", ["전문가", "있는", "전문 가", "안녕하세요."])
def test_plain_hangul_uses_original_render_provenance(text: str):
    output = transform_with_trace(text)
    assert output.normalized_text == text
    assert not output.trace.claim_logs
    assert all(
        piece.provenance.startswith("ORIGINAL_")
        for piece in output.render_pieces
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("FTA은", "에프티에이는"),
        ("AI이", "에이아이이"),
        ("FTA으로", "에프티에이로"),
        ("AI과", "에이아이과"),
    ],
)
def test_generated_surface_particle_policy(text: str, expected: str):
    output = transform_with_trace(text)
    assert output.normalized_text == expected
    assert output.trace.claim_logs
    assert any(
        piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("전문  가", "전문 가"),
        ("안녕하세요 , 반갑습니다", "안녕하세요, 반갑습니다"),
        ("전문가", "전문이"),
        ("있는", "있은"),
    ],
)
def test_forbidden_core_invariance_regressions(text: str, forbidden: str):
    assert transform(text) != forbidden
