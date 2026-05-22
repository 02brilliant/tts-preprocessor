from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_counter_trace_debug_export_records_claim_parse_render_validation() -> None:
    output = transform_with_trace("21명")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "스물한 명"
    assert any(claim.owner == "counter_noun" for claim in output.trace.claim_logs)
    assert any(log.owner == "counter_noun" for log in output.trace.parser_logs)
    assert any(
        log.owner == "counter_noun" and log.provenance == "GENERATED_READING"
        for log in output.trace.render_logs
    )
    assert all(log.passed for log in output.trace.validation_logs)


def test_emergency_ambiguous_counter_fallback_records_counter_claim() -> None:
    output = transform_with_trace("112명")

    assert output.normalized_text == "백십이 명"
    assert not any(claim.owner == "emergency" for claim in output.trace.claim_logs)
    assert any(claim.owner == "counter_noun" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "number" for claim in output.trace.claim_logs)
