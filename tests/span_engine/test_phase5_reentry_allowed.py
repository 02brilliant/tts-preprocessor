from __future__ import annotations

from engine.span_engine import ClaimedRange, SourceSpan
from engine.span_engine.claim_registry import SurfaceClaimRegistry


def test_reentry_allowed_surface_claim_allows_nested_claim() -> None:
    registry = SurfaceClaimRegistry()
    parent = ClaimedRange(
        SourceSpan(0, 5),
        "protected_parent",
        "surface",
        reentry_allowed=True,
    )
    child = ClaimedRange(SourceSpan(1, 3), "child", "surface")

    registry.claim(parent)
    assert registry.can_claim(SourceSpan(1, 3), "child") is True
    registry.claim(child)

    assert registry.claims == [parent, child]


def test_lock_and_shadow_claims_block_overlapping_surface_claims() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(ClaimedRange(SourceSpan(0, 2), "tokenizer", "lock"))
    registry.claim(ClaimedRange(SourceSpan(2, 3), "shadow", "shadow"))

    assert registry.can_claim(SourceSpan(1, 2), "number") is False
    assert registry.can_claim(SourceSpan(2, 3), "number") is False
    assert registry.is_blocked(SourceSpan(1, 2)) is True
    assert registry.is_blocked(SourceSpan(2, 3)) is True
