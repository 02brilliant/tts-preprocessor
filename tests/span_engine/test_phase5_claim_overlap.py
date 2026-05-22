from __future__ import annotations

import pytest

from engine.span_engine import ClaimedRange, SourceSpan
from engine.span_engine.claim_registry import SurfaceClaimRegistry


def test_surface_claim_overlap_is_rejected_and_logged() -> None:
    registry = SurfaceClaimRegistry()
    existing = ClaimedRange(SourceSpan(0, 3), "number", "surface")
    registry.claim(existing)

    assert registry.can_claim(SourceSpan(1, 2), "math_numeric") is False
    with pytest.raises(ValueError):
        registry.claim(ClaimedRange(SourceSpan(1, 2), "math_numeric", "surface"))

    assert registry.claims == [existing]
    assert len(registry.collision_logs) == 1
    collision = registry.collision_logs[0]
    assert collision.existing_owner == "number"
    assert collision.attempted_owner == "math_numeric"
    assert collision.existing_span == SourceSpan(0, 3)
    assert collision.attempted_span == SourceSpan(1, 2)
    assert collision.reason


def test_find_overlaps_returns_registered_claim_order() -> None:
    registry = SurfaceClaimRegistry()
    first = ClaimedRange(SourceSpan(0, 2), "a", "surface")
    second = ClaimedRange(SourceSpan(3, 5), "b", "surface")
    third = ClaimedRange(SourceSpan(6, 8), "c", "surface")
    registry.claim(first)
    registry.claim(second)
    registry.claim(third)

    assert registry.find_overlaps(SourceSpan(1, 4)) == [first, second]
    assert registry.find_overlaps(SourceSpan(2, 3)) == []
    assert registry.find_overlaps(SourceSpan(5, 6)) == []
    assert registry.find_overlaps(SourceSpan(7, 9)) == [third]


def test_exact_same_span_different_owner_is_rejected_even_when_existing_allows_reentry() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(
        ClaimedRange(
            SourceSpan(0, 3),
            "parent",
            "surface",
            reentry_allowed=True,
        )
    )

    assert registry.can_claim(SourceSpan(0, 3), "child") is False
    with pytest.raises(ValueError):
        registry.claim(ClaimedRange(SourceSpan(0, 3), "child", "surface"))
