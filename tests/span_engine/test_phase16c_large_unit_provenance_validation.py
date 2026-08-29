from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_large_unit_atomic_provenance_and_validation() -> None:
    output = transform_with_trace("수량은 3만입니다")

    assert output.normalized_text == "수량은 삼만입니다"
    assert any(
        piece.owner == "large_unit_atomic"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "만" in piece.text
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_large_unit_registered_counter_provenance_and_validation() -> None:
    output = transform_with_trace("3만개")

    assert output.normalized_text == "삼만-개"
    assert any(
        piece.owner == "counter_noun"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.owner == "counter_noun"
        and piece.provenance == "ORIGINAL_KOREAN"
        and piece.text == "개"
        for piece in output.render_pieces
    )
    assert all(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_large_unit_atomic_safe_particle_must_not_broad_correct() -> None:
    output = transform_with_trace("3만를")

    assert output.normalized_text == "삼만를"
    assert not any(
        getattr(log, "metadata", {}).get("marker") == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.particle_exception_logs
    )
