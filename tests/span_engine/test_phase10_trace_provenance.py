from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_currency_trace_debug_export_records_owner_parse_render_and_particle() -> None:
    output = transform_with_trace("€50을 냈다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "오십-유로를 냈다"
    assert any(claim.owner == "currency" for claim in output.trace.claim_logs)
    assert any(log.owner == "currency" for log in output.trace.parser_logs)
    assert any(log.owner == "currency" and log.provenance == "GENERATED_READING" for log in output.trace.render_logs)
    assert output.trace.particle_exception_logs
    assert all(log.passed for log in output.trace.validation_logs)


def test_unit_trace_debug_export_records_owner_parse_and_validation() -> None:
    output = transform_with_trace("50kg입니다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "오십-킬로그램입니다"
    assert any(claim.owner == "simple_unit" for claim in output.trace.claim_logs)
    assert any(log.owner == "simple_unit" for log in output.trace.parser_logs)
    assert all(log.passed for log in output.trace.validation_logs)
