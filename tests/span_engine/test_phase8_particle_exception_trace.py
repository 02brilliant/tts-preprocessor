from __future__ import annotations

import json

from engine.span_engine import SourceSpan, output_to_debug_dict, transform_with_trace


def test_particle_exception_trace_records_consumed_marker() -> None:
    output = transform_with_trace("FTA은 적용됐다")

    assert output.trace.particle_exception_logs
    log = output.trace.particle_exception_logs[0]
    assert log.stage == "particle_exception"
    assert log.raw == "은"
    assert log.actual == "는"
    assert log.owner == "dictionary"
    assert log.reason == "safe_post_surface_particle_exception"
    assert log.action == "replace_particle"
    assert log.metadata["marker"] == "PARTICLE_EXCEPTION_CONSUMED"
    assert log.metadata["original_particle"] == "은"
    assert log.metadata["generated_particle"] == "는"
    assert log.metadata["surface_span"] == SourceSpan(0, 3)


def test_particle_exception_debug_export_is_json_safe() -> None:
    debug = output_to_debug_dict(transform_with_trace("AI을 적용했다"))

    json.dumps(debug, ensure_ascii=False)
    particle_logs = debug["trace"]["particle_exception_logs"]
    assert particle_logs
    assert particle_logs[0]["metadata"]["marker"] == "PARTICLE_EXCEPTION_CONSUMED"
    assert particle_logs[0]["metadata"]["surface_span"] == {
        "start": 0,
        "end": 2,
        "length": 2,
    }


def test_noop_i_particle_trace_preserves_original_piece() -> None:
    output = transform_with_trace("AI이 적용됐다")

    assert any(
        log.action == "preserve_particle"
        and log.decision == "noop"
        and log.raw == "이"
        for log in output.trace.particle_exception_logs
    )
    assert any(piece.text == "이" and piece.provenance == "ORIGINAL_KOREAN" for piece in output.render_pieces)
    assert not any(piece.provenance == "GENERATED_PARTICLE" for piece in output.render_pieces)


def test_risky_particle_has_no_generated_particle_or_exception_log() -> None:
    output = transform_with_trace("AI가 적용됐다")

    assert output.normalized_text == "에이아이가 적용됐다"
    assert not any(piece.provenance == "GENERATED_PARTICLE" for piece in output.render_pieces)
    assert output.trace.particle_exception_logs == []
