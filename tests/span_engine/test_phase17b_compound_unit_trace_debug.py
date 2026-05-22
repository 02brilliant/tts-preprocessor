from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_phase17b_slash_trace_debug() -> None:
    output = transform_with_trace("10MB/s")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "compound_slash_unit" for claim in output.trace.claim_logs)
    assert any(log.owner == "compound_slash_unit" for log in output.trace.parser_logs)
    assert any(log.owner == "compound_slash_unit" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phase17b_exact_trace_debug() -> None:
    output = transform_with_trace("60fps")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "compound_exact_unit" for claim in output.trace.claim_logs)
    assert any(log.owner == "compound_exact_unit" for log in output.trace.parser_logs)
    assert any(log.owner == "compound_exact_unit" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phase17b_bracket_trace_debug() -> None:
    output = transform_with_trace("[10MB/s]")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.trace.bracket_filter_logs
    assert not any(
        claim.owner in {"compound_slash_unit", "compound_exact_unit"}
        for claim in output.trace.claim_logs
    )
