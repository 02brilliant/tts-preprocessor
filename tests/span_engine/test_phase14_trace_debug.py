from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_event_trace_debug_export() -> None:
    output = transform_with_trace("12.12 사태")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "event" for claim in output.trace.claim_logs)
    assert any(
        log.stage == "event_gate" and log.decision == "pass"
        for log in output.trace.gate_logs
    )
    assert any(log.owner == "event" for log in output.trace.parser_logs)
    assert any(log.owner == "event" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_one_digit_event_trace_debug_export() -> None:
    output = transform_with_trace("12.3 비상계엄")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    # Phase 28B: Expected to fail until Phase 28C
    assert any(claim.owner == "event" for claim in output.trace.claim_logs)
    assert any(
        log.stage == "event_gate" and log.decision == "pass"
        for log in output.trace.gate_logs
    )
    assert any(log.owner == "event" for log in output.trace.parser_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_emergency_trace_debug_export() -> None:
    output = transform_with_trace("긴급번호 112는")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "emergency" for claim in output.trace.claim_logs)
    assert any(
        log.stage == "emergency_gate" and log.decision == "pass"
        for log in output.trace.gate_logs
    )
    assert any(log.owner == "emergency" for log in output.trace.parser_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_emergency_fallback_trace_debug_export() -> None:
    output = transform_with_trace("112명")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "백십이 명"
    assert not any(claim.owner == "emergency" for claim in output.trace.claim_logs)
    assert any(claim.owner == "counter_noun" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)
    assert any(
        log.stage == "emergency_gate" and log.reason == "disallowed_tail"
        for log in output.trace.gate_logs
    )
