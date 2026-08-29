from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_currency_generated_reading_uses_safe_particle_exception() -> None:
    output = transform_with_trace("€50을 냈다")

    assert output.normalized_text == "오십-유로를 냈다"
    assert any(piece.text == "오십-유로" and piece.provenance == "GENERATED_READING" for piece in output.render_pieces)
    assert any(piece.text == "를" and piece.provenance == "GENERATED_PARTICLE" for piece in output.render_pieces)
    assert any(log.metadata.get("marker") == "PARTICLE_EXCEPTION_CONSUMED" for log in output.trace.particle_exception_logs)
    assert all(log.passed for log in output.trace.validation_logs)


def test_unit_generated_reading_uses_safe_particle_exception() -> None:
    output = transform_with_trace("100MB을 넘는다")

    assert output.normalized_text == "백-메가바이트를 넘는다"
    assert any(piece.text == "백-메가바이트" and piece.owner == "simple_unit" for piece in output.render_pieces)
    assert any(piece.text == "를" and piece.provenance == "GENERATED_PARTICLE" for piece in output.render_pieces)
    assert all(log.passed for log in output.trace.validation_logs)
