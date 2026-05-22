from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan


def span_overlaps_excluded_ranges(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


def is_decimal_like_url_or_path_context(raw_text: str, span: SourceSpan) -> bool:
    left_context = raw_text[max(0, span.start - 10) : span.start]
    if "://" in left_context:
        return True
    return span.start > 0 and raw_text[span.start - 1] == "/"


__all__ = [
    "is_decimal_like_url_or_path_context",
    "span_overlaps_excluded_ranges",
]
