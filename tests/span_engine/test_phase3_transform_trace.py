from __future__ import annotations

from engine.span_engine import TransformTrace, transform, transform_with_trace


def test_transform_with_trace_runs_source_map_tokenizer_and_pass_through_render() -> None:
    raw_text = "AI는 123입니다"
    output = transform_with_trace(raw_text)

    assert output.normalized_text == "에이아이는 백이십삼입니다"
    assert "".join(piece.text for piece in output.render_pieces) == "에이아이는 백이십삼입니다"
    assert isinstance(output.trace, TransformTrace)
    assert output.trace.source_map_logs
    assert output.trace.tokenization_logs
    assert output.trace.render_logs


def test_transform_with_trace_records_provenance_from_tokenization() -> None:
    output = transform_with_trace("안녕하세요,")

    assert [piece.provenance for piece in output.render_pieces] == [
        "ORIGINAL_KOREAN",
        "ORIGINAL_PUNCT",
    ]


def test_transform_remains_string_pass_through() -> None:
    assert transform("AI는 123입니다") == "에이아이는 백이십삼입니다"
