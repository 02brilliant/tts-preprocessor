from __future__ import annotations

import pytest

from engine.pipeline.surfaces import SurfaceType, surface_from_type
from engine.pipeline.transform_engine import normalize_text, transform_text


@pytest.mark.parametrize(
    ("text", "expected_text", "expected_type", "expected_surface_text", "expected_particle"),
    [
        ("1대1로", "일대일로", SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE, "일대일", "로"),
        ("60여 명이", "육십여 명이", SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE, "육십여 명", "이"),
        ("1만3천여 명을", "만 삼천여 명을", SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE, "만 삼천여 명", "을"),
        ("제62회는", "제육십이회는", SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE, "제육십이회", "는"),
    ],
)
def test_trailing_particle_is_separated_from_typed_surface(
    text: str,
    expected_text: str,
    expected_type: SurfaceType,
    expected_surface_text: str,
    expected_particle: str,
):
    result = normalize_text(text)
    assert result.text == expected_text
    assert len(result.rendered_surfaces) == 1

    surface = result.rendered_surfaces[0].surface
    assert surface.surface_type == expected_type
    assert surface.surface_text == expected_surface_text
    assert surface.trailing_particle == expected_particle
    assert surface.allow_particle_attachment


@pytest.mark.parametrize(
    ("text", "expected_surface_text", "expected_particle"),
    [
        ("MFN율은", "엠에프엔율", "은"),
        ("AI기반은", "에이아이기반", "은"),
        ("3~8cm는", "삼에서 팔 센티미터", "는"),
        ("1∼11월은", "일에서 십일월", "은"),
    ],
)
def test_mixed_token_surface_keeps_atomic_body_when_particle_attaches(
    text: str,
    expected_surface_text: str,
    expected_particle: str,
):
    result = normalize_text(text)
    assert len(result.rendered_surfaces) == 1

    surface = result.rendered_surfaces[0].surface
    assert surface.surface_text == expected_surface_text
    assert surface.trailing_particle == expected_particle


def test_legacy_string_helper_does_not_receive_typed_surface_placeholder(monkeypatch: pytest.MonkeyPatch):
    from engine.pipeline import transform_engine

    original = transform_engine._fix_numeric_postpositions
    seen: list[str] = []

    def guarded(text: str) -> str:
        seen.append(text)
        assert "__surface__" not in text, text
        return original(text)

    monkeypatch.setattr(transform_engine, "_fix_numeric_postpositions", guarded)
    result = normalize_text("MFN율은 제62회는 1대1로 3~8cm는 60여 명이 참여했다")

    assert result.text == "엠에프엔율은 제육십이회는 일대일로 삼에서 팔 센티미터는 육십여 명이 참여했다"
    assert seen


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("MFN율", "엠에프엔율"),
        ("KBS기자", "케이비에스기자"),
        ("AI기반", "에이아이기반"),
        ("SK하이닉스", "에스케이하이닉스"),
        ("제5차", "제오차"),
        ("제62회", "제육십이회"),
        ("60여 명", "육십여 명"),
        ("1만3천여 명", "만 삼천여 명"),
        ("1대1", "일대일"),
        ("3에서 8cm", "삼에서 팔 센티미터"),
        ("1에서 5cm", "일에서 오 센티미터"),
        ("3~8cm", "삼에서 팔 센티미터"),
        ("1∼11월", "일에서 십일월"),
        ("8만 9천 개", "팔만 구천 개"),
    ],
)
def test_controlled_mixed_token_expansion_end_to_end(text: str, expected: str):
    assert transform_text(text) == expected


def test_controlled_mixed_token_expansion_sentence_end_to_end():
    text = "MFN율은 제62회는 1대1로 3에서 8cm 범위와 8만 9천 개를 포함한다"
    expected = "엠에프엔율은 제육십이회는 일대일로 삼에서 팔 센티미터 범위와 팔만 구천 개를 포함한다"
    assert transform_text(text) == expected


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("FTA는", "에프티에 이"),
        ("AI가", "에이아가"),
        ("전문가", "전문이"),
        ("있는", "있은"),
        ("6402억", "육천사백이 억"),
        ("K-푸드", "케가-"),
        ("3~8cm", "삼~8"),
        ("MFN율은", "엠에프엔 율은"),
        ("3~8cm는", "삼에서 팔 cm는"),
    ],
)
def test_forbidden_outputs_remain_blocked(text: str, forbidden: str):
    assert transform_text(text) != forbidden


def test_non_attachable_lexical_surface_rejects_particle_attachment():
    lexical_surface = surface_from_type("기자", SurfaceType.LEXICAL_TOKEN, source_stage="test")
    assert not lexical_surface.allow_particle_attachment
    with pytest.raises(ValueError):
        lexical_surface.attach_particle("가")


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_surface_text"),
    [
        ("K-푸드가", SurfaceType.SINGLE_LETTER_HYPHEN_SURFACE, "케이-푸드"),
        ("AI·반도체는", SurfaceType.LEXICAL_MIDDLEDOT_SURFACE, "에이아이 반도체"),
    ],
)
def test_non_attachable_protected_surfaces_keep_particle_outside_surface_body(
    text: str,
    expected_type: SurfaceType,
    expected_surface_text: str,
):
    result = normalize_text(text)
    assert len(result.rendered_surfaces) == 1

    surface = result.rendered_surfaces[0].surface
    assert surface.surface_type == expected_type
    assert surface.surface_text == expected_surface_text
    assert surface.trailing_particle is None
    assert not surface.allow_particle_attachment
