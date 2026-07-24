from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_large_unit_atomic_trace_debug() -> None:
    output = transform_with_trace("3만")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "large_unit_atomic" for claim in output.trace.claim_logs)
    assert any(log.owner == "large_unit_atomic" for log in output.trace.parser_logs)
    assert any(log.owner == "large_unit_atomic" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_large_unit_atomic_bracket_trace_debug() -> None:
    output = transform_with_trace("[3만]")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.trace.bracket_filter_logs
    assert not any(
        claim.owner == "large_unit_atomic" for claim in output.trace.claim_logs
    )


def test_large_unit_registered_counter_full_claim_trace_debug() -> None:
    output = transform_with_trace("3만개")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "삼만 개"
    assert not any(
        claim.owner == "large_unit_atomic" for claim in output.trace.claim_logs
    )
    assert any(
        claim.owner == "counter_noun"
        and claim.reason == "counter_large_unit_core_full_consume"
        for claim in output.trace.claim_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
