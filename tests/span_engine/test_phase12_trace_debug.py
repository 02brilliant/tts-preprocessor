from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_range_with_unit_trace_debug_export() -> None:
    output = transform_with_trace("3~8cm")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "range_with_unit" for claim in output.trace.claim_logs)
    assert any(log.owner == "range_with_unit" for log in output.trace.parser_logs)
    assert any(
        log.owner == "range_with_unit" and log.provenance == "GENERATED_READING"
        for log in output.trace.render_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_korean_suffix_range_trace_debug_export() -> None:
    output = transform_with_trace("1~11월")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "range" for claim in output.trace.claim_logs)
    assert any(
        piece.text == "월" and piece.provenance == "ORIGINAL_KOREAN"
        for piece in output.render_pieces
    )
