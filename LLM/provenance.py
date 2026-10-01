from __future__ import annotations

import re

from LLM.validation_models import NormalizationSnapshot, NormalizedSpan
from engine.span_engine.models import TransformOutput
from engine.span_engine.protected import protected_literal_spans
from engine.text_alignment import rendered_index_map


_LOCKED_PROVENANCE = frozenset(
    {"GENERATED_READING", "GENERATED_PARTICLE", "GENERATED_PUNCT"}
)
_ADDITIONAL_IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9-])[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}(?![A-Za-z0-9-])"
)


def build_normalization_snapshot(output: TransformOutput) -> NormalizationSnapshot:
    if not isinstance(output, TransformOutput):
        raise TypeError("output must be TransformOutput")
    normalized_text = output.normalized_text
    mapping = rendered_index_map(output)
    spans: list[NormalizedSpan] = []
    if mapping is None and output.render_pieces and normalized_text:
        # Untraceable presentation/fallback edits cannot silently unlock output.
        spans.append(NormalizedSpan(0, len(normalized_text), normalized_text,
                                    None, None, "preserve", "ALIGNMENT_UNRESOLVED",
                                    locked=True, protected=False))
    rendered_cursor = 0
    for piece in output.render_pieces:
        piece_start = rendered_cursor
        piece_end = piece_start + len(piece.text)
        rendered_cursor = piece_end
        if not piece.text:
            continue
        if mapping is None:
            continue
        surviving = [mapping[index] for index in range(piece_start, piece_end) if index in mapping]
        if not surviving:
            continue  # Explicitly elided by the bracket filter, not a lost lock.
        normalized_start, normalized_end = surviving[0], surviving[-1] + 1
        source_span = piece.source_span
        spans.append(
            NormalizedSpan(
                normalized_start=normalized_start,
                normalized_end=normalized_end,
                text=normalized_text[normalized_start:normalized_end],
                source_start=None if source_span is None else source_span.start,
                source_end=None if source_span is None else source_span.end,
                owner=piece.owner,
                provenance=piece.provenance,
                locked=piece.provenance in _LOCKED_PROVENANCE,
                protected=False,
            )
        )

    for protected in (*output.protected_spans, *_llm_protected_spans(normalized_text)):
        spans.append(
            NormalizedSpan(
                normalized_start=protected.start,
                normalized_end=protected.end,
                text=normalized_text[protected.start:protected.end],
                source_start=None,
                source_end=None,
                owner="preserve",
                provenance="PROTECTED_LITERAL",
                locked=True,
                protected=True,
            )
        )
    return NormalizationSnapshot(
        normalized_text=normalized_text,
        spans=tuple(sorted(spans, key=lambda span: (span.normalized_start, span.normalized_end))),
        numeric_annotations=output.numeric_annotations,
    )


def minimal_snapshot(normalized_text: str) -> NormalizationSnapshot:
    spans = tuple(
        NormalizedSpan(
            normalized_start=span.start,
            normalized_end=span.end,
            text=normalized_text[span.start:span.end],
            source_start=None,
            source_end=None,
            owner="preserve",
            provenance="PROTECTED_LITERAL",
            locked=True,
            protected=True,
        )
        for span in _llm_protected_spans(normalized_text)
    )
    return NormalizationSnapshot(normalized_text=normalized_text, spans=spans)


def _llm_protected_spans(text: str):
    spans = list(protected_literal_spans(text))
    for match in _ADDITIONAL_IDENTIFIER_RE.finditer(text):
        if any(match.start() < span.end and span.start < match.end() for span in spans):
            continue
        from engine.span_engine.models import SourceSpan

        spans.append(SourceSpan(match.start(), match.end()))
    return tuple(sorted(spans, key=lambda span: span.start))


__all__ = ["build_normalization_snapshot", "minimal_snapshot"]
