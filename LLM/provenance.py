from __future__ import annotations

from difflib import SequenceMatcher
import re

from LLM.validation_models import NormalizationSnapshot, NormalizedSpan
from engine.span_engine.models import TransformOutput
from engine.span_engine.protected import protected_literal_spans


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
    rendered_text = "".join(piece.text for piece in output.render_pieces)
    mapping = _matching_index_map(rendered_text, normalized_text)
    spans: list[NormalizedSpan] = []
    rendered_cursor = 0
    for piece in output.render_pieces:
        piece_start = rendered_cursor
        piece_end = piece_start + len(piece.text)
        rendered_cursor = piece_end
        if not piece.text:
            continue
        final_range = _project_range(piece_start, piece_end, mapping)
        if final_range is None:
            continue
        normalized_start, normalized_end = final_range
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

    for protected in _llm_protected_spans(normalized_text):
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


def _matching_index_map(source: str, target: str) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for block in SequenceMatcher(a=source, b=target, autojunk=False).get_matching_blocks():
        for offset in range(block.size):
            mapping[block.a + offset] = block.b + offset
    return mapping


def _llm_protected_spans(text: str):
    spans = list(protected_literal_spans(text))
    for match in _ADDITIONAL_IDENTIFIER_RE.finditer(text):
        if any(match.start() < span.end and span.start < match.end() for span in spans):
            continue
        from engine.span_engine.models import SourceSpan

        spans.append(SourceSpan(match.start(), match.end()))
    return tuple(sorted(spans, key=lambda span: span.start))


def _project_range(
    start: int,
    end: int,
    mapping: dict[int, int],
) -> tuple[int, int] | None:
    projected = [mapping.get(index) for index in range(start, end)]
    if not projected or any(index is None for index in projected):
        return None
    indexes = [index for index in projected if index is not None]
    if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        return None
    return indexes[0], indexes[-1] + 1


__all__ = ["build_normalization_snapshot", "minimal_snapshot"]
