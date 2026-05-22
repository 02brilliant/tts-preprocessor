from __future__ import annotations

import pytest

from engine.span_engine import ClaimedRange, SourceSpan
from engine.span_engine.claim_registry import SurfaceClaimRegistry


def test_preserve_claim_blocks_reentry_and_unsafe_fallback() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(
        ClaimedRange(
            SourceSpan(0, 4),
            "event",
            "preserve",
            reason="one_digit_right_block",
        )
    )

    assert registry.can_claim(SourceSpan(0, 4), "math_numeric") is False
    assert registry.can_claim(SourceSpan(1, 3), "number") is False
    assert registry.is_blocked(SourceSpan(0, 4)) is True
    assert registry.is_blocked(SourceSpan(1, 3)) is True

    with pytest.raises(ValueError):
        registry.claim(ClaimedRange(SourceSpan(1, 3), "number", "surface"))

    assert registry.collision_logs[-1].reason == "preserve_claim_blocks_reentry"


def test_gate_fail_reentry_allowed_false_blocks_overlap() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(ClaimedRange(SourceSpan(0, 4), "time", "gate_fail"))

    assert registry.can_claim(SourceSpan(1, 3), "number") is False
    assert registry.is_blocked(SourceSpan(1, 3)) is True


def test_gate_fail_reentry_allowed_true_does_not_block_later_claim() -> None:
    registry = SurfaceClaimRegistry()
    gate_fail = ClaimedRange(
        SourceSpan(0, 4),
        "time",
        "gate_fail",
        reentry_allowed=True,
    )
    later_claim = ClaimedRange(SourceSpan(1, 3), "number", "surface")
    registry.claim(gate_fail)

    assert registry.can_claim(SourceSpan(1, 3), "number") is True
    assert registry.is_blocked(SourceSpan(1, 3)) is False

    registry.claim(later_claim)
    assert registry.claims == [gate_fail, later_claim]
