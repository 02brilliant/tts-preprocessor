from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_date_trace_debug_export() -> None:
    output = transform_with_trace("날짜는 2025-01-03입니다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "date" for claim in output.trace.claim_logs)
    assert any(log.owner == "date" for log in output.trace.parser_logs)
    assert any(log.owner == "date" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_time_trace_debug_export() -> None:
    output = transform_with_trace("회의는 13:05에 시작한다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "time" for claim in output.trace.claim_logs)
    assert any(log.owner == "time" for log in output.trace.parser_logs)
    assert any(
        log.stage == "time_gate" and log.decision == "pass"
        for log in output.trace.gate_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
