from __future__ import annotations

from engine.span_engine import RenderPiece, ShadowUnit, SourceSpan, transform_with_trace
from engine.span_engine.validation import validate_shadow


def test_consumed_particle_span_is_not_shadow_validation_failure() -> None:
    output = transform_with_trace("FTA은 적용됐다")

    assert output.normalized_text == "에프티에이는 적용됐다"
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(
        log.actual == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.validation_logs
    )


def test_safe_particle_exception_consumes_number_particle_span() -> None:
    output = transform_with_trace("3를 더했다")

    assert output.normalized_text == "삼을 더했다"
    assert all(log.passed for log in output.trace.validation_logs)
    assert any(
        log.metadata.get("marker") == "PARTICLE_EXCEPTION_CONSUMED"
        for log in output.trace.particle_exception_logs
    )


def test_noop_and_risky_particles_are_validated_as_original_korean() -> None:
    noop = transform_with_trace("AI이 적용됐다")
    risky = transform_with_trace("AI가 적용됐다")

    assert noop.normalized_text == "에이아이이 적용됐다"
    assert risky.normalized_text == "에이아이가 적용됐다"
    assert any(log.expected == "이" and log.actual == "이" for log in noop.trace.validation_logs)
    assert any(log.expected == "가" and log.actual == "가" for log in risky.trace.validation_logs)


def test_shadow_validation_does_not_use_final_string_korean_for_particle_exception() -> None:
    shadow = [ShadowUnit("KOREAN_LITERAL", "은", SourceSpan(3, 4))]
    pieces = [
        RenderPiece(
            "에프티에이는",
            "GENERATED_READING",
            SourceSpan(0, 4),
            owner="dictionary",
        )
    ]

    assert validate_shadow(pieces, shadow).passed is False
    consumed = validate_shadow(pieces, shadow, consumed_particle_spans={(3, 4)})
    assert consumed.passed is True
    assert consumed.logs[0].actual == "PARTICLE_EXCEPTION_CONSUMED"
