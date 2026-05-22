from __future__ import annotations

import json

import pytest

from engine.span_engine import output_to_debug_dict, transform_with_trace


def test_phase18b_prosody_comma_trace_expected() -> None:
    output = transform_with_trace("그리고 우리는 결과를 확인했다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "그리고, 우리는 결과를 확인했다"
    assert any(
        piece.owner == "prosody"
        and piece.provenance == "GENERATED_PUNCT"
        and piece.text == ","
        and piece.metadata.get("prosody_type") == "comma"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
    assert getattr(output.trace, "prosody_logs", [])


def test_phase18b_existing_comma_keeps_output_without_extra_prosody_piece() -> None:
    output = transform_with_trace("그리고, 우리는 결과를 확인했다")
    debug = output_to_debug_dict(output)

    json.dumps(debug, ensure_ascii=False)
    assert output.normalized_text == "그리고, 우리는 결과를 확인했다"
    assert not any(
        piece.owner == "prosody"
        and piece.provenance == "GENERATED_PUNCT"
        and piece.text == ","
        for piece in output.render_pieces
    )


def test_phase18b_generated_surface_internal_comma_must_not_appear() -> None:
    output = transform_with_trace("그리고 90km/h입니다")

    assert output.normalized_text == "그리고, 시속 구십 킬로미터입니다"
    assert "시속, 구십 킬로미터" not in output.normalized_text
