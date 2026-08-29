from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_phase17c_admin_suffix_provenance_and_validation() -> None:
    output = transform_with_trace("종로3가")

    assert output.normalized_text == "종로 삼-가"
    assert any(
        piece.owner == "administrative_suffix"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "종로" in piece.text
        for piece in output.render_pieces
    )
    assert any(
        piece.provenance == "ORIGINAL_KOREAN" and "가" in piece.text
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_phase17c_admin_suffix_particle_must_not_broad_correct() -> None:
    output = transform_with_trace("종로3가는")

    assert output.normalized_text == "종로 삼-가는"
    assert not any(
        getattr(log, "metadata", {}).get("marker") == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.particle_exception_logs
    )


def test_phase17c_admin_suffix_no_claim_without_anchor() -> None:
    output = transform_with_trace("3가 맞다")

    assert output.normalized_text == "삼가 맞다"
    assert not any(
        piece.owner == "administrative_suffix"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
