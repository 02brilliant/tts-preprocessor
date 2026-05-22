from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_signed_temperature_trace_debug() -> None:
    output = transform_with_trace("-2.5℃")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "signed_temperature" for claim in output.trace.claim_logs)
    assert any(log.owner == "signed_temperature" for log in output.trace.parser_logs)
    assert any(
        log.owner == "signed_temperature" for log in output.trace.render_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_signed_degree_trace_debug() -> None:
    output = transform_with_trace("+3°")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "signed_degree" for claim in output.trace.claim_logs)
    assert any(log.owner == "signed_degree" for log in output.trace.parser_logs)


def test_unsigned_special_unit_trace_debug_stays_unsigned() -> None:
    output = transform_with_trace("5℃")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "special_unit" for claim in output.trace.claim_logs)
    assert not any(
        claim.owner == "signed_temperature" for claim in output.trace.claim_logs
    )
