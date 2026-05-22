from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_jamo_provenance_and_validation() -> None:
    output = transform_with_trace("입력 ㄱㄴㄷ")

    assert output.normalized_text == "입력 기역 니은 디귿"
    assert any(
        piece.owner == "jamo" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_jamo_safe_particle_and_validation() -> None:
    output = transform_with_trace("ㄱ는")

    assert output.normalized_text == "기역은"
    assert any(
        piece.owner == "jamo" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        getattr(log, "metadata", {}).get("marker") == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.particle_exception_logs
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_jamo_mixed_adjacency_preserve_validation() -> None:
    output = transform_with_trace("ㄱAI")

    assert output.normalized_text == "ㄱAI"
    assert not any(
        piece.owner == "jamo" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
