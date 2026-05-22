from __future__ import annotations

import pytest

from engine.prosody.comma import insert_commas
from engine.pipeline.surfaces import SurfaceType
from engine.pipeline.transform_engine import normalize_text


@pytest.mark.parametrize(
    ("text", "expected_text", "expected_types"),
    [
        ("FTA는", "에프티에이는", (SurfaceType.ALLOWED_ACRONYM_WITH_PARTICLE,)),
        ("AI·반도체", "에이아이 반도체", (SurfaceType.LEXICAL_MIDDLEDOT_SURFACE,)),
        ("K-푸드", "케이-푸드", (SurfaceType.SINGLE_LETTER_HYPHEN_SURFACE,)),
        ("3~8cm", "삼에서 팔 센티미터", (SurfaceType.RANGE_SURFACE,)),
        ("6402억", "육천사백이억", (SurfaceType.LARGE_UNIT_ATOMIC_SURFACE,)),
        ("-1.3도", "마이너스 일쩜삼도", (SurfaceType.SIGNED_DEGREE_SURFACE,)),
        ("12·12 사태", "십이십이 사태", (SurfaceType.EVENT_SURFACE,)),
    ],
)
def test_normalize_text_emits_typed_surface_spans(text: str, expected_text: str, expected_types: tuple[SurfaceType, ...]):
    result = normalize_text(text)
    assert result.text == expected_text
    assert tuple(span.surface.surface_type for span in result.rendered_surfaces) == expected_types


def test_typed_surface_spans_remain_available_for_prosody_boundaries():
    result = normalize_text("그리고 FTA는 유지하고 AI·반도체 전략은 6402억 달러 규모다")
    assert [span.surface.surface_type for span in result.rendered_surfaces] == [
        SurfaceType.ALLOWED_ACRONYM_WITH_PARTICLE,
        SurfaceType.LEXICAL_MIDDLEDOT_SURFACE,
        SurfaceType.LARGE_UNIT_ATOMIC_SURFACE,
    ]
    assert all(span.surface.opaque for span in result.rendered_surfaces)
    assert all(not span.surface.allow_prosody_inside for span in result.rendered_surfaces)


def test_insert_commas_accepts_normalization_result_and_respects_surface_boundaries():
    result = normalize_text("그리고 FTA는 유지하고 AI·반도체 전략은 6402억 달러 규모다")
    assert insert_commas(result) == "그리고, 에프티에이는 유지하고 에이아이 반도체 전략은 육천사백이억 달러 규모다"


def test_insert_commas_respects_range_surface_boundaries():
    result = normalize_text("3~8cm 범위로 자란다")
    assert insert_commas(result) == "삼에서 팔 센티미터 범위로 자란다"
