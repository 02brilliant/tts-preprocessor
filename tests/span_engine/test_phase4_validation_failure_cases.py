from __future__ import annotations

import pytest

from engine.span_engine import RenderPiece, ShadowUnit, SourceSpan
from engine.span_engine.validation import validate_shadow


def _first_failed_reason(pieces: list[RenderPiece], shadow: list[ShadowUnit]) -> str | None:
    result = validate_shadow(pieces, shadow)
    assert result.passed is False
    failed = [log for log in result.logs if not log.passed]
    assert failed
    return failed[0].reason


def test_validation_fails_when_original_korean_text_changes() -> None:
    result = validate_shadow(
        [RenderPiece("전문이", "ORIGINAL_KOREAN", SourceSpan(0, 3))],
        [ShadowUnit("KOREAN_LITERAL", "전문가", SourceSpan(0, 3))],
    )

    assert result.passed is False
    failed = [log for log in result.logs if not log.passed][0]
    assert failed.expected == "전문가"
    assert failed.actual == "전문이"
    assert failed.reason == "original_text_mismatch"


def test_validation_fails_when_original_korean_piece_is_missing() -> None:
    assert (
        _first_failed_reason([], [ShadowUnit("KOREAN_LITERAL", "가", SourceSpan(0, 1))])
        == "missing_original_piece"
    )


def test_validation_fails_when_generated_reading_replaces_original_korean() -> None:
    assert (
        _first_failed_reason(
            [RenderPiece("명", "GENERATED_READING", SourceSpan(2, 3))],
            [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))],
        )
        == "provenance_mismatch"
    )


def test_validation_fails_when_source_span_is_wrong() -> None:
    assert (
        _first_failed_reason(
            [RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(3, 4))],
            [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))],
        )
        == "source_span_mismatch"
    )


def test_validation_fails_when_original_space_changes() -> None:
    result = validate_shadow(
        [RenderPiece(" ", "ORIGINAL_SPACE", SourceSpan(2, 4))],
        [ShadowUnit("KOREAN_SPACE", "  ", SourceSpan(2, 4))],
    )

    assert result.passed is False
    failed = [log for log in result.logs if not log.passed][0]
    assert failed.expected == "  "
    assert failed.actual == " "
    assert failed.reason == "original_text_mismatch"


def test_validation_fails_when_korean_punctuation_changes() -> None:
    result = validate_shadow(
        [RenderPiece(".", "ORIGINAL_PUNCT", SourceSpan(5, 6))],
        [ShadowUnit("KOREAN_PUNCT", ",", SourceSpan(5, 6))],
    )

    assert result.passed is False
    failed = [log for log in result.logs if not log.passed][0]
    assert failed.expected == ","
    assert failed.actual == "."
    assert failed.reason == "original_text_mismatch"


def test_validation_fails_on_duplicate_original_piece_key() -> None:
    result = validate_shadow(
        [
            RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(2, 3)),
            RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(2, 3)),
        ],
        [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))],
    )

    assert result.passed is False
    assert any(log.reason == "duplicate_original_piece" for log in result.logs)


@pytest.mark.parametrize(
    "piece",
    [
        RenderPiece("명", "GENERATED_READING", SourceSpan(2, 3)),
        RenderPiece("명", "GENERATED_PARTICLE", SourceSpan(2, 3)),
        RenderPiece("명", "GENERATED_PUNCT", SourceSpan(2, 3)),
        RenderPiece("명", "ORIGINAL_KOREAN", None),
    ],
)
def test_generated_or_unmapped_piece_cannot_satisfy_original_shadow(piece: RenderPiece) -> None:
    result = validate_shadow([piece], [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))])

    assert result.passed is False
