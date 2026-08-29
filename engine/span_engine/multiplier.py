from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import HYBRID_COUNTER_THRESHOLD, native_number_under_100
from engine.span_engine.models import RenderPiece, SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    normalize_integer_text,
    read_decimal_text,
    read_spaced_integer_value,
)
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY

_INTEGER_RE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_NUMBER_RE = rf"{_INTEGER_RE}(?:\.\d+)?"
_MULTIPLIER_RE = re.compile(rf"(?P<number>{_NUMBER_RE})(?P<space> ?)(?P<suffix>배)")
_PREV_BLOCKERS = frozenset("+-–—.,~:/_")


def scan_multiplier_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _MULTIPLIER_RE.finditer(raw_text):
        number_span = SourceSpan(match.start("number"), match.end("number"))
        suffix_span = SourceSpan(match.start("suffix"), match.end("suffix"))
        full_span = SourceSpan(match.start("number"), match.end("suffix"))
        if _span_overlaps_excluded_range(full_span, excluded_ranges):
            continue
        if not _valid_boundary(raw_text, number_span, suffix_span):
            continue
        number = match.group("number")
        reading = multiplier_number_reading(number)
        if reading is None:
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=number_span,
                full_span=full_span,
                owner="multiplier",
                surface_type="MULTIPLIER_SURFACE",
                suffix_spans=[suffix_span],
                reason="multiplier_bae_owner",
                metadata={
                    "number": number,
                    "reading": reading,
                    "suffix_span": suffix_span,
                },
            )
        )
    return candidates


def parse_multiplier_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "multiplier":
        return None
    reading = candidate.metadata.get("reading")
    return f"{reading}{SPOKEN_NUMERIC_BOUNDARY}배" if isinstance(reading, str) else None


def multiplier_render_pieces(
    raw_text: str, candidate: SurfaceCandidate
) -> list[RenderPiece] | None:
    if candidate.owner != "multiplier":
        return None
    reading = candidate.metadata.get("reading")
    suffix_span = _suffix_span(candidate)
    if not isinstance(reading, str) or suffix_span is None:
        return None
    return [
        RenderPiece(
            text=f"{reading}{SPOKEN_NUMERIC_BOUNDARY}",
            provenance="GENERATED_READING",
            source_span=candidate.core_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=raw_text[suffix_span.start : suffix_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=suffix_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]


def multiplier_number_reading(raw_number: str) -> str | None:
    if not isinstance(raw_number, str):
        raise TypeError("raw_number must be str")
    if "." in raw_number:
        return read_decimal_text(raw_number)

    normalized = normalize_integer_text(raw_number)
    if normalized is None:
        return None
    value = int(normalized)
    if 1 <= value <= HYBRID_COUNTER_THRESHOLD:
        return native_number_under_100(value)
    try:
        return read_spaced_integer_value(value)
    except ValueError:
        return None


def _suffix_span(candidate: SurfaceCandidate) -> SourceSpan | None:
    if candidate.suffix_spans:
        return candidate.suffix_spans[0]
    suffix_span = candidate.metadata.get("suffix_span")
    return suffix_span if isinstance(suffix_span, SourceSpan) else None


def _valid_boundary(
    raw_text: str, number_span: SourceSpan, suffix_span: SourceSpan
) -> bool:
    prev_char = raw_text[number_span.start - 1] if number_span.start > 0 else None
    next_char = raw_text[suffix_span.end] if suffix_span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in {"/", "_"}:
        return False
    return True


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "multiplier_number_reading",
    "multiplier_render_pieces",
    "parse_multiplier_candidate",
    "scan_multiplier_candidates",
]
