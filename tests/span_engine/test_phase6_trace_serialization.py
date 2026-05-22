from __future__ import annotations

import json

from engine.span_engine import (
    ClaimCollisionLog,
    RenderPiece,
    ShadowUnit,
    SourceSpan,
    TraceLogEntry,
    TransformTrace,
    transform_with_trace,
)
from engine.span_engine.trace import (
    claim_collision_log_to_dict,
    output_to_debug_dict,
    render_piece_to_dict,
    shadow_unit_to_dict,
    span_to_dict,
    trace_log_entry_to_dict,
    trace_to_dict,
)


def _assert_json_safe(value: object) -> None:
    json.dumps(value, ensure_ascii=False)
    assert "SourceSpan" not in repr(value)
    assert "RenderPiece" not in repr(value)
    assert "ShadowUnit" not in repr(value)


def test_span_to_dict_includes_length() -> None:
    assert span_to_dict(SourceSpan(2, 5)) == {"start": 2, "end": 5, "length": 3}
    assert span_to_dict(None) is None


def test_dataclass_log_serializers_return_json_safe_dicts() -> None:
    piece_dict = render_piece_to_dict(
        RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(2, 3), owner="counter")
    )
    shadow_dict = shadow_unit_to_dict(ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3)))
    collision_dict = claim_collision_log_to_dict(
        ClaimCollisionLog("math_numeric", SourceSpan(1, 2), "number", SourceSpan(0, 3), "overlap")
    )
    entry_dict = trace_log_entry_to_dict(
        TraceLogEntry("render", "piece_created", SourceSpan(0, 1), raw="가")
    )

    assert piece_dict["source_span"]["length"] == 1
    assert shadow_dict["span"]["start"] == 2
    assert collision_dict["attempted_span"]["start"] == 1
    assert entry_dict["span"] == {"start": 0, "end": 1, "length": 1}
    _assert_json_safe([piece_dict, shadow_dict, collision_dict, entry_dict])


def test_trace_to_dict_contains_all_log_categories_and_is_json_safe() -> None:
    trace = TransformTrace()
    trace.source_map_logs.append(TraceLogEntry("source_map", "built", raw="전문"))
    trace.render_logs.append(RenderPiece("전문", "ORIGINAL_KOREAN", SourceSpan(0, 2)))

    trace_dict = trace_to_dict(trace)

    for key in [
        "source_map_logs",
        "tokenization_logs",
        "shadow_logs",
        "claim_logs",
        "claim_collision_logs",
        "gate_logs",
        "parser_logs",
        "fallback_logs",
        "preserve_logs",
        "particle_exception_logs",
        "render_logs",
        "validation_logs",
        "prosody_logs",
        "bracket_filter_logs",
    ]:
        assert key in trace_dict
    _assert_json_safe(trace_dict)


def test_output_to_debug_dict_for_transform_output_is_json_safe() -> None:
    output = transform_with_trace("전문  가")
    debug_dict = output_to_debug_dict(output)

    assert debug_dict["normalized_text"] == "전문  가"
    assert debug_dict["render_pieces"]
    assert debug_dict["trace"]["source_map_logs"]
    _assert_json_safe(debug_dict)
