from __future__ import annotations

from engine.span_engine import TransformTrace, transform, transform_with_trace


def test_transform_with_trace_has_claim_registry_logs_for_one_digit_event() -> None:
    raw_text = "12.3 비상계엄"
    output = transform_with_trace(raw_text)

    # Phase 28B: Expected to fail until Phase 28C
    assert output.normalized_text == "십이삼 비상계엄"
    assert isinstance(output.trace, TransformTrace)
    assert any(log.owner == "event" for log in output.trace.claim_logs)
    assert output.trace.claim_collision_logs == []
    assert output.trace.validation_logs
    assert all(log.passed for log in output.trace.validation_logs)
    assert transform(raw_text) == "십이삼 비상계엄"
