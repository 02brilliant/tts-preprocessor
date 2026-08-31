from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan

_FILE_LIKE_MALFORMED_NUMERIC_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9._-]*\.\.\d+(?:\.[A-Za-z0-9]+)?"
)


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


def file_like_malformed_numeric_token_span(
    raw_text: str, span: SourceSpan
) -> SourceSpan | None:
    for match in _FILE_LIKE_MALFORMED_NUMERIC_RE.finditer(raw_text):
        token_span = SourceSpan(match.start(), match.end())
        if token_span.start <= span.start and span.end <= token_span.end:
            return token_span
    return None


def is_file_like_malformed_numeric_context(raw_text: str, span: SourceSpan) -> bool:
    return file_like_malformed_numeric_token_span(raw_text, span) is not None


def iter_file_like_malformed_numeric_spans(raw_text: str):
    for match in _FILE_LIKE_MALFORMED_NUMERIC_RE.finditer(raw_text):
        yield SourceSpan(match.start(), match.end())


__all__ = [
    "file_like_malformed_numeric_token_span",
    "is_decimal_like_url_or_path_context",
    "is_file_like_malformed_numeric_context",
    "iter_file_like_malformed_numeric_spans",
    "span_overlaps_excluded_ranges",
]
