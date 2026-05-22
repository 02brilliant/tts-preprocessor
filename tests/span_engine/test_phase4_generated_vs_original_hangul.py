from __future__ import annotations

from engine.span_engine import RenderPiece, ShadowUnit, SourceSpan
from engine.span_engine.validation import validate_shadow


def test_generated_hangul_reading_does_not_fail_when_original_suffix_is_preserved() -> None:
    result = validate_shadow(
        [
            RenderPiece("스물한", "GENERATED_READING", SourceSpan(0, 2), owner="counter_noun"),
            RenderPiece("명", "ORIGINAL_KOREAN", SourceSpan(2, 3), owner="counter_noun"),
        ],
        [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))],
    )

    assert result.passed is True


def test_generated_hangul_cannot_replace_original_korean_suffix() -> None:
    result = validate_shadow(
        [
            RenderPiece("스물한", "GENERATED_READING", SourceSpan(0, 2), owner="counter_noun"),
            RenderPiece("명", "GENERATED_READING", SourceSpan(2, 3), owner="counter_noun"),
        ],
        [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))],
    )

    assert result.passed is False
    assert any(log.reason == "provenance_mismatch" for log in result.logs)


def test_generated_acronym_reading_can_coexist_with_original_korean_suffix() -> None:
    result = validate_shadow(
        [
            RenderPiece("에프티에이", "GENERATED_READING", SourceSpan(0, 3), owner="acronym_suffix"),
            RenderPiece("율", "ORIGINAL_KOREAN", SourceSpan(3, 4), owner="acronym_suffix"),
        ],
        [ShadowUnit("KOREAN_LITERAL", "율", SourceSpan(3, 4))],
    )

    assert result.passed is True


def test_generated_acronym_reading_cannot_cover_original_korean_suffix_span() -> None:
    result = validate_shadow(
        [
            RenderPiece("에프티에이율", "GENERATED_READING", SourceSpan(0, 4), owner="acronym_suffix"),
        ],
        [ShadowUnit("KOREAN_LITERAL", "율", SourceSpan(3, 4))],
    )

    assert result.passed is False


def test_final_string_korean_does_not_count_without_original_provenance() -> None:
    result = validate_shadow(
        [
            RenderPiece("스물한 명", "GENERATED_READING", SourceSpan(0, 3), owner="counter_noun"),
        ],
        [ShadowUnit("KOREAN_LITERAL", "명", SourceSpan(2, 3))],
    )

    assert result.passed is False
