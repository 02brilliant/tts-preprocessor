from __future__ import annotations

import json

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_square_bracket_trace_debug_shape() -> None:
    debug = output_to_debug_dict(transform_with_trace("가격은 [3kg]입니다"))

    json.dumps(debug, ensure_ascii=False)
    logs = debug["trace"]["bracket_filter_logs"]
    assert any(
        log["event"] == "square_bracket_unwrapped"
        and log["action"] == "unwrap_square_brackets"
        and log["reason"] == "final_bracket_filter"
        and log["metadata"]["bracket_type"] == "square"
        for log in logs
    )


def test_parenthesis_trace_debug_shape() -> None:
    debug = output_to_debug_dict(transform_with_trace("문장(임시)입니다"))

    json.dumps(debug, ensure_ascii=False)
    logs = debug["trace"]["bracket_filter_logs"]
    assert any(
        log["event"] == "parenthesis_elided"
        and log["action"] == "delete_parenthesis_content"
        and log["reason"] == "final_bracket_filter"
        and log["metadata"]["bracket_type"] == "parenthesis"
        for log in logs
    )
