from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_hyphen_digit_block_trace_debug() -> None:
    output = transform_with_trace("123-456-7890")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "hyphen_digit_blocks" for claim in output.trace.claim_logs)
    assert any(log.owner == "hyphen_digit_blocks" for log in output.trace.parser_logs)
    assert any(log.owner == "hyphen_digit_blocks" for log in output.trace.render_logs)
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phone_route_trace_debug() -> None:
    output = transform_with_trace("1234-5678")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "phone" for claim in output.trace.claim_logs)
    assert any(log.owner == "phone" for log in output.trace.parser_logs)


def test_date_precedence_trace_debug() -> None:
    output = transform_with_trace("2025-01-03")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert any(claim.owner == "date" for claim in output.trace.claim_logs)
    assert not any(claim.owner == "hyphen_digit_blocks" for claim in output.trace.claim_logs)


def test_ascii_hyphen_ambiguous_preserve_trace_debug() -> None:
    output = transform_with_trace("1-2")

    assert output.normalized_text == "1-2"
    assert len(output.trace.claim_logs) == 1
    claim = output.trace.claim_logs[0]
    assert claim.owner == "preserve"
    assert claim.reason == "invalid_basic_arithmetic_expression_preserve"
    assert all(
        piece.provenance == "ORIGINAL_BOUNDARY"
        for piece in output.render_pieces
    )

