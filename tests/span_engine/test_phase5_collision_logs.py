from __future__ import annotations

import pytest

from engine.span_engine import ClaimCollisionLog, ClaimedRange, SourceSpan
from engine.span_engine.claim_registry import SurfaceClaimRegistry


def test_collision_log_contains_attempted_and_existing_claim_details() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(ClaimedRange(SourceSpan(0, 3), "number", "surface"))

    with pytest.raises(ValueError):
        registry.claim(ClaimedRange(SourceSpan(1, 2), "math_numeric", "surface"))

    assert len(registry.collision_logs) == 1
    log = registry.collision_logs[0]
    assert isinstance(log, ClaimCollisionLog)
    assert log.attempted_owner == "math_numeric"
    assert log.attempted_span == SourceSpan(1, 2)
    assert log.existing_owner == "number"
    assert log.existing_span == SourceSpan(0, 3)
    assert log.reason


def test_claim_collision_log_metadata_default_is_independent() -> None:
    log1 = ClaimCollisionLog("a", SourceSpan(0, 1), "b", SourceSpan(1, 2), "reason")
    log2 = ClaimCollisionLog("a", SourceSpan(0, 1), "b", SourceSpan(1, 2), "reason")

    log1.metadata["x"] = 1

    assert "x" not in log2.metadata
