from __future__ import annotations

from engine.span_engine.models import RenderPiece, SourceSpan
from engine.span_engine.prosody import apply_prosody_comma_adapter
from engine.span_engine.prosody_extra import apply_extra_prosody_comma_adapter
from engine.span_engine.render import join_render_pieces


def _original_provenance(char: str) -> str:
    if char.isspace():
        return "ORIGINAL_SPACE"
    if "\uac00" <= char <= "\ud7a3":
        return "ORIGINAL_KOREAN"
    if char in ".,:;!?()[]{}<>-~·∼～/":
        return "ORIGINAL_PUNCT"
    return "ORIGINAL_BOUNDARY"


def apply_span_prosody(text: str) -> str:
    pieces = [
        RenderPiece(
            text=char,
            provenance=_original_provenance(char),
            source_span=SourceSpan(index, index + 1),
        )
        for index, char in enumerate(text)
    ]
    primary = apply_prosody_comma_adapter(pieces, text)
    extra = apply_extra_prosody_comma_adapter(primary.pieces, text)
    return join_render_pieces(extra.pieces)
