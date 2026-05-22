from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_phase17b_slash_inventory_provenance_and_validation() -> None:
    output = transform_with_trace("전송률은 10MB/s입니다")

    assert output.normalized_text == "전송률은 초당 십 메가바이트입니다"
    assert any(
        piece.owner == "compound_slash_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "전송률은" in piece.text
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phase17b_exact_inventory_provenance_and_validation() -> None:
    output = transform_with_trace("화질은 60fps입니다")

    assert output.normalized_text == "화질은 육십 에프피에스입니다"
    assert any(
        piece.owner == "compound_exact_unit"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "화질은" in piece.text
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phase17b_exact_particle_exception_trace() -> None:
    output = transform_with_trace("60fps은 낮다")

    assert output.normalized_text == "육십 에프피에스는 낮다"
    assert any(
        getattr(log, "metadata", {}).get("marker") == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.particle_exception_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
