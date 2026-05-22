from __future__ import annotations

import pytest

from engine.span_engine import SourceSpan, SpanToken


def test_locked_span_token_kinds_become_immutable() -> None:
    assert SpanToken("KOREAN_LITERAL", "안녕", SourceSpan(0, 2)).immutable is True
    assert SpanToken("SPACE_LOCK", "  ", SourceSpan(2, 4)).immutable is True
    assert SpanToken("PUNCT_LOCK", ",", SourceSpan(4, 5)).immutable is True


def test_plain_and_boundary_and_surface_tokens() -> None:
    plain = SpanToken("PLAIN", "123", SourceSpan(0, 3))
    boundary = SpanToken("BOUNDARY_LITERAL", "[", SourceSpan(0, 1))
    surface = SpanToken(
        "SURFACE",
        "AI",
        SourceSpan(0, 2),
        owner="dictionary",
        surface_type="ACRONYM_SURFACE",
    )

    assert plain.immutable is False
    assert boundary.immutable is False
    assert surface.owner == "dictionary"
    assert surface.surface_type == "ACRONYM_SURFACE"


@pytest.mark.parametrize(
    ("kind", "raw", "span", "immutable"),
    [
        ("INVALID", "x", SourceSpan(0, 1), False),
        ("PLAIN", 123, SourceSpan(0, 1), False),
        ("PLAIN", "x", (0, 1), False),
        ("PLAIN", "x", SourceSpan(0, 1), "yes"),
    ],
)
def test_span_token_rejects_invalid_values(
    kind: object, raw: object, span: object, immutable: object
) -> None:
    with pytest.raises((TypeError, ValueError)):
        SpanToken(kind, raw, span, immutable=immutable)  # type: ignore[arg-type]


def test_span_token_metadata_is_independent_per_instance() -> None:
    token1 = SpanToken("PLAIN", "1", SourceSpan(0, 1))
    token2 = SpanToken("PLAIN", "2", SourceSpan(1, 2))

    token1.metadata["x"] = 1

    assert "x" not in token2.metadata
