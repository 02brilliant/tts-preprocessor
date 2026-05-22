from __future__ import annotations

from engine.span_engine.models import RenderPiece, SourceSpan, SpanToken, Surface


TOKEN_PROVENANCE = {
    "KOREAN_LITERAL": "ORIGINAL_KOREAN",
    "SPACE_LOCK": "ORIGINAL_SPACE",
    "PUNCT_LOCK": "ORIGINAL_PUNCT",
    "BOUNDARY_LITERAL": "ORIGINAL_BOUNDARY",
    "PLAIN": "ORIGINAL_BOUNDARY",
    "SURFACE": "ORIGINAL_BOUNDARY",
}


def render_token(token: SpanToken) -> RenderPiece:
    if not isinstance(token, SpanToken):
        raise TypeError("token must be SpanToken")
    return RenderPiece(
        text=token.raw,
        provenance=TOKEN_PROVENANCE[token.kind],
        source_span=token.span,
        owner=token.owner,
    )


def render_tokens_pass_through(tokens: list[SpanToken]) -> list[RenderPiece]:
    if not isinstance(tokens, list):
        raise TypeError("tokens must be list[SpanToken]")
    return [render_token(token) for token in tokens]


def render_tokens_with_surfaces(
    raw_text: str, tokens: list[SpanToken], surfaces: list[Surface]
) -> list[RenderPiece]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(tokens, list):
        raise TypeError("tokens must be list[SpanToken]")
    if not isinstance(surfaces, list):
        raise TypeError("surfaces must be list[Surface]")
    for token in tokens:
        if not isinstance(token, SpanToken):
            raise TypeError("tokens must contain SpanToken")
    for surface in surfaces:
        if not isinstance(surface, Surface):
            raise TypeError("surfaces must contain Surface")
        if surface.reading is None:
            raise ValueError("surface reading is required for generated render")

    pieces: list[RenderPiece] = []
    sorted_surfaces = sorted(surfaces, key=lambda surface: surface.span.start)
    cursor = 0
    for surface in sorted_surfaces:
        if surface.span.start < cursor:
            raise ValueError("surfaces must not overlap")
        pieces.extend(_render_original_range(raw_text, tokens, cursor, surface.span.start))
        if surface.render_pieces is not None:
            pieces.extend(surface.render_pieces)
        else:
            pieces.append(
                RenderPiece(
                    text=surface.reading or "",
                    provenance="GENERATED_READING",
                    source_span=surface.span,
                    owner=surface.owner,
                    metadata={"surface_type": surface.surface_type},
                )
            )
        cursor = surface.span.end
    pieces.extend(_render_original_range(raw_text, tokens, cursor, len(raw_text)))
    return pieces


def join_render_pieces(pieces: list[RenderPiece]) -> str:
    if not isinstance(pieces, list):
        raise TypeError("pieces must be list[RenderPiece]")
    for piece in pieces:
        if not isinstance(piece, RenderPiece):
            raise TypeError("pieces must contain RenderPiece")
    return "".join(piece.text for piece in pieces)


def _render_original_range(
    raw_text: str, tokens: list[SpanToken], start: int, end: int
) -> list[RenderPiece]:
    if start == end:
        return []
    pieces: list[RenderPiece] = []
    for token in tokens:
        overlap_start = max(start, token.span.start)
        overlap_end = min(end, token.span.end)
        if overlap_start >= overlap_end:
            continue
        if overlap_start == token.span.start and overlap_end == token.span.end:
            pieces.append(render_token(token))
            continue
        fragment_span = SourceSpan(overlap_start, overlap_end)
        pieces.append(
            RenderPiece(
                text=raw_text[overlap_start:overlap_end],
                provenance=TOKEN_PROVENANCE[token.kind],
                source_span=fragment_span,
                owner=token.owner,
            )
        )
    return pieces


__all__ = [
    "TOKEN_PROVENANCE",
    "join_render_pieces",
    "render_token",
    "render_tokens_pass_through",
    "render_tokens_with_surfaces",
]
