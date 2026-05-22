from __future__ import annotations

import json

import pytest

from engine.span_engine import ClaimedRange, SourceSpan
from engine.span_engine.claim_registry import SurfaceClaimRegistry
from engine.span_engine.trace import claim_collision_log_to_dict


def test_claim_collision_log_serializes_to_debug_dict() -> None:
    registry = SurfaceClaimRegistry()
    registry.claim(ClaimedRange(SourceSpan(0, 3), "number", "surface"))

    with pytest.raises(ValueError):
        registry.claim(ClaimedRange(SourceSpan(1, 2), "math_numeric", "surface"))

    log_dict = claim_collision_log_to_dict(registry.collision_logs[0])

    json.dumps(log_dict, ensure_ascii=False)
    assert log_dict["attempted_owner"] == "math_numeric"
    assert log_dict["existing_owner"] == "number"
    assert log_dict["attempted_span"] == {"start": 1, "end": 2, "length": 1}
    assert log_dict["existing_span"] == {"start": 0, "end": 3, "length": 3}
    assert log_dict["reason"]
