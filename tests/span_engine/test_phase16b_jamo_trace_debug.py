from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_jamo_trace_debug() -> None:
    output = transform_with_trace("ㄱㄴㄷ")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "jamo" for claim in output.trace.claim_logs)
    assert any(log.owner == "jamo" for log in output.trace.parser_logs)
    assert any(log.owner == "jamo" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_jamo_bracket_trace_debug() -> None:
    output = transform_with_trace("[ㄱㄴㄷ]")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(log.stage == "bracket_filter" for log in output.trace.bracket_filter_logs)
    assert not any(claim.owner == "jamo" for claim in output.trace.claim_logs)

