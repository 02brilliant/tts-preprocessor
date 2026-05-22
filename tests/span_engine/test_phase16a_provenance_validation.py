from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_signed_temperature_provenance_and_validation() -> None:
    output = transform_with_trace("온도는 -2.5℃입니다")

    assert output.normalized_text == "온도는 영하 이쩜오도입니다"
    assert any(
        piece.owner == "signed_temperature"
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_signed_degree_provenance_and_validation() -> None:
    output = transform_with_trace("각도는 +3°를 표시")

    assert output.normalized_text == "각도는 플러스 삼도를 표시"
    assert any(
        piece.owner == "signed_degree" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)


def test_signed_unit_provenance_validation() -> None:
    output = transform_with_trace("-3kg")

    assert output.normalized_text == "마이너스 삼 킬로그램"
    assert not any(
        piece.owner in {"signed_temperature", "signed_degree"}
        and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(
        piece.owner == "simple_unit" and piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
    assert any(getattr(log, "passed", False) for log in output.trace.validation_logs)
