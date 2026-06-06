from __future__ import annotations

from engine.span_engine import transform_with_trace


def test_shadow_validation_passes_with_dictionary_generated_reading() -> None:
    output = transform_with_trace("GPT는")

    assert output.normalized_text == "지피티는"
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(piece.text == "는" and piece.provenance == "GENERATED_PARTICLE" for piece in output.render_pieces)
    assert any(piece.text == "지피티" and piece.provenance == "GENERATED_READING" for piece in output.render_pieces)


def test_shadow_validation_passes_with_number_generated_reading() -> None:
    output = transform_with_trace("123입니다")

    assert output.normalized_text == "백이십삼입니다"
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(piece.text == "입니다" and piece.provenance == "ORIGINAL_KOREAN" for piece in output.render_pieces)
    assert any(piece.text == "백이십삼" and piece.provenance == "GENERATED_READING" for piece in output.render_pieces)


def test_original_korean_before_generated_surface_is_preserved() -> None:
    output = transform_with_trace("전문가 AI")

    assert output.normalized_text == "전문가 에이아이"
    assert any(piece.text == "전문가" and piece.provenance == "ORIGINAL_KOREAN" for piece in output.render_pieces)
    assert any(piece.text == "에이아이" and piece.provenance == "GENERATED_READING" for piece in output.render_pieces)
