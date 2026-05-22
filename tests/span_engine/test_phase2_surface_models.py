from __future__ import annotations

import pytest

from engine.span_engine import (
    ClaimedRange,
    RenderPiece,
    SourceSpan,
    Surface,
    SurfaceCandidate,
)


def test_surface_accepts_acronym_with_trailing_particle() -> None:
    surface = Surface(
        surface_type="ACRONYM_SURFACE",
        owner="dictionary",
        raw="FTA",
        span=SourceSpan(0, 3),
        reading="에프티에이",
        trailing_particle="은",
        trailing_particle_span=SourceSpan(3, 4),
    )

    assert surface.protected is True
    assert surface.allow_reentry is False
    assert surface.allow_prosody_inside is False
    assert surface.trailing_particle == "은"


def test_surface_accepts_counter_render_pieces_with_mixed_provenance() -> None:
    pieces = [
        RenderPiece(
            "스물한",
            "GENERATED_READING",
            SourceSpan(0, 2),
            owner="counter_noun",
        ),
        RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(2, 3), owner="counter_noun"),
    ]
    surface = Surface(
        surface_type="COUNTER_SURFACE",
        owner="counter_noun",
        raw="21명",
        span=SourceSpan(0, 3),
        render_pieces=pieces,
    )

    assert surface.render_pieces == pieces


def test_surface_rejects_trailing_particle_span_without_particle() -> None:
    with pytest.raises((TypeError, ValueError)):
        Surface(
            surface_type="ACRONYM_SURFACE",
            owner="dictionary",
            raw="FTA",
            span=SourceSpan(0, 3),
            trailing_particle_span=SourceSpan(3, 4),
        )


def test_surface_metadata_is_independent_per_instance() -> None:
    surface1 = Surface("TYPE", "owner", "a", SourceSpan(0, 1))
    surface2 = Surface("TYPE", "owner", "b", SourceSpan(1, 2))

    surface1.metadata["x"] = 1

    assert "x" not in surface2.metadata


def test_surface_candidate_accepts_core_full_suffix_and_particle_spans() -> None:
    counter_candidate = SurfaceCandidate(
        core_span=SourceSpan(0, 2),
        full_span=SourceSpan(0, 3),
        owner="counter_noun",
        suffix_spans=[SourceSpan(2, 3)],
    )
    acronym_candidate = SurfaceCandidate(
        core_span=SourceSpan(0, 3),
        full_span=SourceSpan(0, 4),
        owner="dictionary",
        trailing_particle_span=SourceSpan(3, 4),
    )
    admin_candidate = SurfaceCandidate(
        core_span=SourceSpan(2, 3),
        full_span=SourceSpan(0, 4),
        owner="administrative_suffix",
        suffix_spans=[SourceSpan(0, 2), SourceSpan(3, 4)],
    )

    assert counter_candidate.suffix_spans == [SourceSpan(2, 3)]
    assert acronym_candidate.trailing_particle_span == SourceSpan(3, 4)
    assert admin_candidate.core_span == SourceSpan(2, 3)


def test_surface_candidate_rejects_core_span_outside_full_span() -> None:
    with pytest.raises(ValueError):
        SurfaceCandidate(
            core_span=SourceSpan(0, 3),
            full_span=SourceSpan(1, 4),
            owner="number",
        )


def test_surface_candidate_rejects_invalid_suffix_span() -> None:
    with pytest.raises((TypeError, ValueError)):
        SurfaceCandidate(
            core_span=SourceSpan(0, 1),
            full_span=SourceSpan(0, 2),
            owner="x",
            suffix_spans=[(1, 2)],  # type: ignore[list-item]
        )


def test_surface_candidate_mutable_defaults_are_independent() -> None:
    candidate1 = SurfaceCandidate(SourceSpan(0, 1), SourceSpan(0, 1), "a")
    candidate2 = SurfaceCandidate(SourceSpan(1, 2), SourceSpan(1, 2), "b")

    candidate1.suffix_spans.append(SourceSpan(0, 1))
    candidate1.metadata["x"] = 1

    assert candidate2.suffix_spans == []
    assert "x" not in candidate2.metadata


@pytest.mark.parametrize(
    "claimed_range",
    [
        ClaimedRange(
            SourceSpan(0, 4),
            "event",
            "preserve",
            reason="one_digit_right_block",
        ),
        ClaimedRange(
            SourceSpan(0, 2),
            "number",
            "surface",
            surface_type="MATH_NUMERIC_SURFACE",
        ),
        ClaimedRange(SourceSpan(0, 3), "shadow", "shadow"),
    ],
)
def test_claimed_range_accepts_allowed_claim_types(claimed_range: ClaimedRange) -> None:
    assert claimed_range.reentry_allowed is False


def test_claimed_range_rejects_invalid_claim_type() -> None:
    with pytest.raises((TypeError, ValueError)):
        ClaimedRange(SourceSpan(0, 1), "owner", "invalid")
