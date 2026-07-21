from __future__ import annotations

from engine.span_engine import SourceSpan, output_to_debug_dict, transform_with_trace
from engine.span_engine.trace import trace_log_entry_to_dict


def test_core_trace_projects_successful_surfaces_in_surface_order() -> None:
    output = transform_with_trace("AI는 123입니다")

    assert output.normalized_text == "에이아이는 백이십삼입니다"
    assert [trace_log_entry_to_dict(log) for log in output.trace.parser_logs] == [
        {
            "stage": "parser",
            "event": "surface_parsed",
            "span": {"start": 0, "end": 2, "length": 2},
            "raw": "AI",
            "owner": "acronym_fallback",
            "surface_type": "ACRONYM_FALLBACK_SURFACE",
            "decision": "success",
            "reason": "phase7_owner_parse",
            "action": "create_surface",
            "provenance": None,
            "expected": None,
            "actual": None,
            "metadata": {"reading": "에이아이"},
        },
        {
            "stage": "parser",
            "event": "surface_parsed",
            "span": {"start": 4, "end": 7, "length": 3},
            "raw": "123",
            "owner": "number",
            "surface_type": "NUMBER_SURFACE",
            "decision": "success",
            "reason": "phase7_owner_parse",
            "action": "create_surface",
            "provenance": None,
            "expected": None,
            "actual": None,
            "metadata": {"reading": "백이십삼"},
        },
    ]


def test_core_trace_projects_final_render_pieces_in_piece_order() -> None:
    output = transform_with_trace("AI는 123입니다")
    piece_logs = [
        log for log in output.trace.render_logs if log.event == "render_piece_created"
    ]

    assert [log.raw for log in piece_logs] == [
        piece.text for piece in output.render_pieces
    ]
    assert [log.span for log in piece_logs] == [
        piece.source_span for piece in output.render_pieces
    ]
    assert [log.owner for log in piece_logs] == [
        piece.owner for piece in output.render_pieces
    ]
    assert [log.provenance for log in piece_logs] == [
        piece.provenance for piece in output.render_pieces
    ]
    assert [log.decision for log in piece_logs] == [
        "render_generated",
        "render_generated",
        "render_original",
        "render_generated",
        "render_original",
    ]
    assert all(log.reason == "phase7_surface_render" for log in piece_logs)


def test_generated_prosody_punctuation_keeps_none_source_span_in_trace() -> None:
    output = transform_with_trace("그리고 우리는 결과를 확인했다")
    comma_piece = next(
        piece
        for piece in output.render_pieces
        if piece.provenance == "GENERATED_PUNCT"
    )
    comma_log = next(
        log
        for log in output.trace.render_logs
        if log.event == "render_piece_created" and log.raw == ","
    )

    assert output.normalized_text == "그리고, 우리는 결과를 확인했다"
    assert comma_piece.source_span is None
    assert comma_log.span is None
    assert comma_log.owner == "prosody"
    assert comma_log.provenance == "GENERATED_PUNCT"
    assert comma_log.decision == "render_generated"


def test_slash_alias_log_precedes_piece_projection_and_keeps_source_span() -> None:
    output = transform_with_trace("안녕하세요///")

    assert output.normalized_text == "안녕하세요."
    assert [log.event for log in output.trace.render_logs] == [
        "surface_render_complete",
        "sentence_final_slash_alias_applied",
        "render_piece_created",
        "render_piece_created",
    ]
    assert output.trace.render_logs[1].span == SourceSpan(5, 8)
    assert output.trace.render_logs[-1].span == SourceSpan(5, 8)
    assert output.trace.render_logs[-1].provenance == "GENERATED_PUNCT"


def test_bracket_filter_and_preserve_surface_remain_separate_from_parser_logs() -> None:
    bracketed = transform_with_trace("[1200원]입니다")
    preserved = transform_with_trace("안내 pH 입니다")

    assert bracketed.normalized_text == "1200원입니다"
    assert "".join(piece.text for piece in bracketed.render_pieces) == "[1200원]입니다"
    assert bracketed.trace.parser_logs == []
    assert bracketed.trace.render_logs[0].metadata["pre_filter_text"] == "[1200원]입니다"
    assert [log.event for log in bracketed.trace.bracket_filter_logs] == [
        "square_bracket_unwrapped"
    ]
    assert preserved.normalized_text == "안내 pH 입니다"
    assert preserved.trace.parser_logs == []
    assert all(
        log.decision == "render_original"
        for log in preserved.trace.render_logs
        if log.event == "render_piece_created"
    )


def test_debug_serialization_preserves_trace_and_validation_order() -> None:
    output = transform_with_trace("AI는 123입니다")
    debug = output_to_debug_dict(output)

    assert debug["normalized_text"] == "에이아이는 백이십삼입니다"
    assert [log["owner"] for log in debug["trace"]["parser_logs"]] == [
        "acronym_fallback",
        "number",
    ]
    assert [log["reason"] for log in debug["trace"]["validation_logs"]] == [
        "phase6_validation_summary",
        "particle_exception_consumed",
        "matched_original_piece",
        "matched_original_piece",
    ]
    assert debug["trace"]["validation_logs"][0]["metadata"] == {
        "passed": True,
        "log_count": 3,
    }
    assert [piece["text"] for piece in debug["render_pieces"]] == [
        "에이아이",
        "는",
        " ",
        "백이십삼",
        "입니다",
    ]

