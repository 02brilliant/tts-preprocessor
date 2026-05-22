from __future__ import annotations

from engine.span_engine import ClaimedRange, SourceSpan
from engine.span_engine.claim_registry import SurfaceClaimRegistry


def test_surface_claim_registry_starts_empty() -> None:
    registry = SurfaceClaimRegistry()

    assert registry.claims == []
    assert registry.collision_logs == []
    assert registry.find_overlaps(SourceSpan(0, 1)) == []
    assert registry.can_claim(SourceSpan(0, 1), "number") is True
    assert registry.is_blocked(SourceSpan(0, 1)) is False


def test_non_overlapping_adjacent_claims_are_allowed() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(ClaimedRange(SourceSpan(0, 2), "number", "surface"))
    registry.claim(ClaimedRange(SourceSpan(2, 4), "unit", "surface"))

    assert len(registry.claims) == 2
    assert registry.can_claim(SourceSpan(4, 5), "other") is True
    assert registry.find_overlaps(SourceSpan(2, 3)) == [
        ClaimedRange(SourceSpan(2, 4), "unit", "surface")
    ]
