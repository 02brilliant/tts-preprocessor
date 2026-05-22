from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_compound_slash_unit_provenance_and_validation() -> None:
    output = transform_with_trace("속도는 90km/h입니다")

    assert output.normalized_text == "속도는 시속 구십 킬로미터입니다"
    assert any(
        piece.owner == "compound_slash_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "속도는" in piece.text
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "입니다" in piece.text
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_compound_slash_unit_particle_exception_trace() -> None:
    output = transform_with_trace("90km/h은 빠르다")

    assert output.normalized_text == "시속 구십 킬로미터는 빠르다"
    assert any(
        piece.owner == "compound_slash_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        getattr(log, "metadata", {}).get("marker") == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.particle_exception_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_compound_slash_unit_url_preserve_validation() -> None:
    output = transform_with_trace("http://x/90km/h")

    assert output.normalized_text == "http://x/90km/h"
    assert not any(
        piece.owner == "compound_slash_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
