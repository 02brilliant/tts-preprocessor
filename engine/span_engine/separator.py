from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate

_SPACED_SEPARATOR_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:\s+[·.]\s*|\s*[.]\s+)\d+(?![A-Za-z0-9])")


def scan_spaced_separator_preserve_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _SPACED_SEPARATOR_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="SPACED_SEPARATOR_PRESERVE_SURFACE",
                reason="spaced_separator_no_partial_rewrite",
            )
        )
    return candidates


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = ["scan_spaced_separator_preserve_candidates"]
