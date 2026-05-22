from __future__ import annotations

from engine.span_engine import TransformTrace, transform, transform_with_trace


def test_transform_with_trace_populates_stable_debug_log_categories() -> None:
    raw_text = "AI는 123입니다"
    output = transform_with_trace(raw_text)

    assert output.normalized_text == "에이아이는 백이십삼입니다"
    assert "".join(piece.text for piece in output.render_pieces) == "에이아이는 백이십삼입니다"
    assert isinstance(output.trace, TransformTrace)
    assert output.trace.source_map_logs
    assert output.trace.tokenization_logs
    assert output.trace.shadow_logs
    assert output.trace.render_logs
    assert output.trace.validation_logs
    assert output.trace.claim_logs
    assert {claim.owner for claim in output.trace.claim_logs} == {"dictionary", "number"}
    assert output.trace.claim_collision_logs == []
    assert transform(raw_text) == "에이아이는 백이십삼입니다"


def test_transform_with_trace_summary_logs_include_counts() -> None:
    output = transform_with_trace("AI는 123입니다")
    trace = output.trace
    assert trace is not None

    assert trace.source_map_logs[0].metadata["source_char_count"] == len("AI는 123입니다")
    assert "token_count" in trace.tokenization_logs[0].metadata
    assert "shadow_unit_count" in trace.shadow_logs[0].metadata
    assert "render_piece_count" in trace.render_logs[0].metadata
    assert "passed" in trace.validation_logs[0].metadata
