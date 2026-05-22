from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import COUNTERS_BY_LENGTH
from engine.span_engine.delimiters import (
    COLON_LIKE_DELIMITERS,
    RANGE_LIKE_DELIMITERS,
    TILDE_LIKE_DELIMITERS,
)
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    read_decimal_fraction_digits,
    read_integer_text,
)
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.span_guards import (
    is_decimal_like_url_or_path_context,
    span_overlaps_excluded_ranges,
)

_DECIMAL_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)")

def scan_decimal_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _DECIMAL_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if span_overlaps_excluded_ranges(span, excluded_ranges):
            continue
            
        left, right = match.groups()

        invalid_counter_candidate = _decimal_counter_preserve_candidate(
            raw_text, span
        )
        if invalid_counter_candidate is not None:
            candidates.append(invalid_counter_candidate)
            continue
        
        # Check boundary guards
        prev_char = raw_text[span.start - 1] if span.start > 0 else None
        next_char = raw_text[span.end] if span.end < len(raw_text) else None
        
        # Block numeric-delimited decimal fragments without suppressing legacy
        # decimal fallback before ordinary Korean hyphenated text.
        prev_is_numeric_delimiter = False
        numeric_range_delimiters = RANGE_LIKE_DELIMITERS | TILDE_LIKE_DELIMITERS
        if prev_char in COLON_LIKE_DELIMITERS:
            prev_is_numeric_delimiter = True
        elif prev_char in numeric_range_delimiters and span.start > 1:
            prev_prev = raw_text[span.start - 2]
            prev_is_numeric_delimiter = prev_prev.isdigit() or prev_prev == "-"

        next_is_numeric_delimiter = False
        if next_char in COLON_LIKE_DELIMITERS:
            next_is_numeric_delimiter = True
        elif next_char in numeric_range_delimiters and span.end + 1 < len(raw_text):
            next_next = raw_text[span.end + 1]
            next_is_numeric_delimiter = next_next.isdigit() or next_next == "-"

        # Block if preceded by ascii alnum or dot/comma/middle-dot or slash
        if prev_char is not None:
            if prev_char.isascii() and prev_char.isalnum():
                continue
            if prev_char in {".", ",", "·", "/"} or prev_is_numeric_delimiter:
                continue
            if prev_char == "-" and span.start > 1:
                pprev = raw_text[span.start - 2]
                if pprev.isascii() and pprev.isalpha():
                    # This is B-2.5, preserve it.
                    continue
        
        # Block if followed by ascii alnum or dot/comma/middle-dot or slash
        if next_char is not None:
            if next_char.isascii() and next_char.isalnum():
                continue
            if next_char == ".":
                if span.end + 1 < len(raw_text) and raw_text[span.end + 1].isdigit():
                    continue
            elif next_char in {"·", "/"} or next_is_numeric_delimiter:
                continue
            if (
                next_char == ","
                and span.end + 1 < len(raw_text)
                and raw_text[span.end + 1].isdigit()
            ):
                continue
            if any(raw_text[span.end:].startswith(s) for s in ("가", "호", "동", "번", "로", "길", "번지")):
                # This is 3.5가, preserve it.
                continue
        
        # Check for URL context (e.g., http://x/12.3)
        if is_decimal_like_url_or_path_context(raw_text, span):
            continue

        integer_reading = read_integer_text(left)
        if integer_reading is None and "," not in left and left.isascii() and left.isdigit():
            # Preserve the existing standalone leading-zero decimal fallback
            # behavior. Owner-attached/code-like contexts are still blocked by
            # the surrounding boundary guards before this point.
            value = int(left)
            if value <= 9999:
                integer_reading = number_to_korean_under_10000(value)
        if integer_reading is None:
            continue
        reading = f"{integer_reading}쩜{read_decimal_fraction_digits(right)}"

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="decimal",
                surface_type="DECIMAL_SURFACE",
                reason="decimal_match",
                metadata={"reading": reading},
            )
        )
    return candidates


def _decimal_counter_preserve_candidate(
    raw_text: str, decimal_span: SourceSpan
) -> SurfaceCandidate | None:
    for counter in COUNTERS_BY_LENGTH:
        if not raw_text.startswith(counter, decimal_span.end):
            continue
        counter_end = decimal_span.end + len(counter)
        if not _valid_decimal_counter_boundary(raw_text, decimal_span, counter_end):
            continue
        full_end = _consume_ascii_tail(raw_text, counter_end)
        full_span = SourceSpan(decimal_span.start, full_end)
        return SurfaceCandidate(
            core_span=full_span,
            full_span=full_span,
            owner="preserve",
            surface_type="DECIMAL_COUNTER_PRESERVE_SURFACE",
            reason="decimal_counter_invalid_owner_candidate_preserve",
            metadata={"counter": counter},
        )
    return None


def _valid_decimal_counter_boundary(
    raw_text: str, decimal_span: SourceSpan, counter_end: int
) -> bool:
    prev_char = raw_text[decimal_span.start - 1] if decimal_span.start > 0 else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in {"+", "-", ".", ",", "·", "/", "_"}:
            return False
    next_char = raw_text[counter_end] if counter_end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return True
    if next_char.isspace():
        return True
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    if next_char in {".", ",", "!", "?", ";"}:
        return True
    return False


def _consume_ascii_tail(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isascii() and raw_text[index].isalnum():
        index += 1
    return index

def parse_decimal_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "decimal":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None

__all__ = ["scan_decimal_candidates", "parse_decimal_candidate"]
