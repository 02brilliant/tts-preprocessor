from __future__ import annotations

import pytest

from engine.span_engine import RenderPiece, ShadowUnit, SourceSpan, transform_with_trace
from engine.span_engine.validation import validate_shadow


@pytest.mark.parametrize(
    ("argument", "value", "message"),
    [
        (
            "consumed_particle_spans",
            [],
            "consumed_particle_spans must be set or None",
        ),
        (
            "consumed_shadow_spans",
            [],
            "consumed_shadow_spans must be set or None",
        ),
        (
            "consumed_particle_spans",
            {(1, "2")},
            "consumed_particle_spans must contain (int, int) tuples",
        ),
        (
            "consumed_shadow_spans",
            {(1, 2, 3)},
            "consumed_shadow_spans must contain (int, int) tuples",
        ),
    ],
)
def test_consumed_span_validation_keeps_argument_specific_error_contract(
    argument: str, value: object, message: str
) -> None:
    kwargs = {argument: value}

    with pytest.raises(TypeError) as exc_info:
        validate_shadow([], [], **kwargs)  # type: ignore[arg-type]

    assert str(exc_info.value) == message


def test_validation_input_checks_keep_observable_order() -> None:
    with pytest.raises(TypeError, match=r"^pieces must be list\[RenderPiece\]$"):
        validate_shadow((), ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match=r"^shadow must be list\[ShadowUnit\]$"):
        validate_shadow([], ())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="^pieces must contain RenderPiece$"):
        validate_shadow([object()], [])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="^shadow must contain ShadowUnit$"):
        validate_shadow([], [object()])  # type: ignore[list-item]


def test_exact_original_match_precedes_both_consumed_markers() -> None:
    span = SourceSpan(2, 3)
    result = validate_shadow(
        [RenderPiece("명", "ORIGINAL_KOREAN", span)],
        [ShadowUnit("KOREAN_LITERAL", "명", span)],
        consumed_particle_spans={(2, 3)},
        consumed_shadow_spans={(2, 3)},
    )

    assert result.passed is True
    assert [log.reason for log in result.logs] == ["matched_original_piece"]


def test_particle_consumed_precedes_surface_internal_consumed() -> None:
    span = SourceSpan(2, 3)
    result = validate_shadow(
        [],
        [ShadowUnit("KOREAN_LITERAL", "명", span)],
        consumed_particle_spans={(2, 3)},
        consumed_shadow_spans={(2, 3)},
    )

    assert result.passed is True
    assert result.logs[0].reason == "particle_exception_consumed"
    assert result.logs[0].actual == "PARTICLE_EXCEPTION_CONSUMED"
    assert result.logs[0].metadata == {"marker": "PARTICLE_EXCEPTION_CONSUMED"}


def test_surface_consumed_precedes_provenance_and_source_span_mismatch() -> None:
    span = SourceSpan(2, 3)
    result = validate_shadow(
        [
            RenderPiece("다름", "GENERATED_READING", span),
            RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(4, 5)),
        ],
        [ShadowUnit("KOREAN_LITERAL", "명", span)],
        consumed_shadow_spans={(2, 3)},
    )

    assert result.passed is True
    assert result.logs[0].reason == "surface_internal_consumed"
    assert result.logs[0].actual == "SURFACE_INTERNAL_CONSUMED"
    assert result.logs[0].metadata == {"marker": "SURFACE_INTERNAL_CONSUMED"}


def test_same_span_provenance_mismatch_precedes_same_text_source_mismatch() -> None:
    span = SourceSpan(2, 3)
    result = validate_shadow(
        [
            RenderPiece("생성", "GENERATED_READING", span),
            RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(4, 5)),
        ],
        [ShadowUnit("KOREAN_LITERAL", "명", span)],
    )

    assert result.passed is False
    assert result.logs[0].reason == "provenance_mismatch"
    assert result.logs[0].actual == "생성"
    assert result.logs[0].metadata == {
        "expected_provenance": "ORIGINAL_KOREAN",
        "actual_provenance": "GENERATED_READING",
    }


def test_duplicate_original_logs_are_sorted_and_precede_shadow_decisions() -> None:
    first_span = SourceSpan(9, 10)
    pieces = [
        RenderPiece("첫", "ORIGINAL_KOREAN", first_span),
        RenderPiece("나", "ORIGINAL_KOREAN", SourceSpan(4, 5)),
        RenderPiece("나", "ORIGINAL_KOREAN", SourceSpan(4, 5)),
        RenderPiece("가", "ORIGINAL_KOREAN", SourceSpan(2, 3)),
        RenderPiece("가", "ORIGINAL_KOREAN", SourceSpan(2, 3)),
    ]
    result = validate_shadow(
        pieces,
        [ShadowUnit("KOREAN_LITERAL", "첫", first_span)],
    )

    assert result.passed is False
    assert [log.reason for log in result.logs] == [
        "duplicate_original_piece",
        "duplicate_original_piece",
        "matched_original_piece",
    ]
    assert [log.metadata for log in result.logs[:2]] == [
        {"key": [2, 3, "ORIGINAL_KOREAN"]},
        {"key": [4, 5, "ORIGINAL_KOREAN"]},
    ]
    assert [log.span for log in result.logs[:2]] == [first_span, first_span]


def test_duplicate_generated_piece_key_does_not_independently_fail_validation() -> None:
    pieces = [
        RenderPiece("삼", "GENERATED_READING", SourceSpan(0, 1)),
        RenderPiece("삼", "GENERATED_READING", SourceSpan(0, 1)),
    ]

    result = validate_shadow(pieces, [])

    assert result.passed is True
    assert result.logs == []


def test_transform_trace_keeps_surface_internal_validation_markers() -> None:
    output = transform_with_trace("1 - 2 - 3")

    assert output.normalized_text == "일 - 이 - 삼"
    assert [log.reason for log in output.trace.validation_logs] == [
        "phase6_validation_summary",
        "surface_internal_consumed",
        "surface_internal_consumed",
        "surface_internal_consumed",
        "surface_internal_consumed",
    ]
    assert all(log.passed for log in output.trace.validation_logs)

