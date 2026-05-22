from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_phase17c_admin_suffix_trace_debug() -> None:
    output = transform_with_trace("종로3가")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "administrative_suffix" for claim in output.trace.claim_logs)
    assert any(log.owner == "administrative_suffix" for log in output.trace.parser_logs)
    assert any(log.owner == "administrative_suffix" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phase17c_admin_suffix_preserve_trace_debug() -> None:
    output = transform_with_trace("3가 맞다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert not any(
        claim.owner == "administrative_suffix" for claim in output.trace.claim_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
