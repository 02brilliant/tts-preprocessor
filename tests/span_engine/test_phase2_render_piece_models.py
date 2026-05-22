from __future__ import annotations

import pytest

from engine.span_engine import RenderPiece, ShadowUnit, SourceSpan


@pytest.mark.parametrize(
    ("kind", "raw", "span"),
    [
        ("KOREAN_LITERAL", "명", SourceSpan(2, 3)),
        ("KOREAN_SPACE", "  ", SourceSpan(1, 3)),
        ("KOREAN_PUNCT", ",", SourceSpan(3, 4)),
        ("PARTICLE_LITERAL", "은", SourceSpan(2, 3)),
    ],
)
def test_shadow_unit_accepts_allowed_kinds(kind: str, raw: str, span: SourceSpan) -> None:
    shadow_unit = ShadowUnit(kind, raw, span)

    assert shadow_unit.kind == kind
    assert shadow_unit.raw == raw
    assert shadow_unit.span == span


def test_shadow_unit_rejects_invalid_kind() -> None:
    with pytest.raises((TypeError, ValueError)):
        ShadowUnit("INVALID", "x", SourceSpan(0, 1))


@pytest.mark.parametrize(
    ("text", "provenance", "source_span", "owner"),
    [
        ("명", "ORIGINAL_KOREAN", SourceSpan(2, 3), None),
        (" ", "ORIGINAL_SPACE", SourceSpan(1, 2), None),
        (",", "ORIGINAL_PUNCT", SourceSpan(3, 4), None),
        ("[", "ORIGINAL_BOUNDARY", SourceSpan(0, 1), None),
        ("스물한", "GENERATED_READING", SourceSpan(0, 2), "counter_noun"),
        ("는", "GENERATED_PARTICLE", None, "dictionary"),
        (",", "GENERATED_PUNCT", None, "prosody"),
    ],
)
def test_render_piece_accepts_allowed_provenance(
    text: str, provenance: str, source_span: SourceSpan | None, owner: str | None
) -> None:
    piece = RenderPiece(text, provenance, source_span, owner=owner)

    assert piece.text == text
    assert piece.provenance == provenance
    assert piece.source_span == source_span
    assert piece.owner == owner


def test_render_piece_rejects_invalid_provenance() -> None:
    with pytest.raises((TypeError, ValueError)):
        RenderPiece("x", "UNKNOWN", SourceSpan(0, 1))


def test_render_piece_metadata_is_independent_per_instance() -> None:
    piece1 = RenderPiece("a", "ORIGINAL_BOUNDARY", SourceSpan(0, 1))
    piece2 = RenderPiece("b", "ORIGINAL_BOUNDARY", SourceSpan(1, 2))

    piece1.metadata["x"] = 1

    assert "x" not in piece2.metadata
