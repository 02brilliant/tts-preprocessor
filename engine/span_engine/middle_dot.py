from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.number import SINO_DIGITS, number_to_korean_under_10000
from engine.span_engine.span_guards import (
    is_decimal_like_url_or_path_context,
    span_overlaps_excluded_ranges,
)

_MIDDLE_DOT_RE = re.compile(r"(\d+)(·\d+)+")

def scan_middle_dot_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _MIDDLE_DOT_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if span_overlaps_excluded_ranges(span, excluded_ranges):
            continue
            
        # Boundary guards (similar to decimal.py)
        prev_char = raw_text[span.start - 1] if span.start > 0 else None
        next_char = raw_text[span.end] if span.end < len(raw_text) else None
        
        # Block if preceded by ascii alnum or dot/comma/middle-dot or slash
        if prev_char is not None:
            if prev_char.isascii() and prev_char.isalnum():
                continue
            if prev_char in {".", ",", "·", "/"}:
                continue
            if prev_char == "-" and span.start > 1:
                pprev = raw_text[span.start - 2]
                if pprev.isascii() and pprev.isalpha():
                    # Preserve e.g. B-12.3
                    continue
        
        # Block if followed by ascii alnum or dot/comma/middle-dot or slash
        if next_char is not None:
            if next_char.isascii() and next_char.isalnum():
                continue
            if next_char in {".", "·", "/"}:
                continue
            if (
                next_char == ","
                and span.end + 1 < len(raw_text)
                and raw_text[span.end + 1].isdigit()
            ):
                continue
            if any(raw_text[span.end:].startswith(s) for s in ("가", "호", "동", "번", "로", "길", "번지")):
                continue

        # URL/Path context guard
        if is_decimal_like_url_or_path_context(raw_text, span):
            continue

        blocks = match.group(0).split("·")
        reading = middle_dot_number_reading(blocks)

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="middle_dot_numeric",
                surface_type="LEXICAL_MIDDLEDOT_SURFACE",
                reason="middle_dot_numeric_block_match",
                metadata={"reading": reading, "blocks": blocks},
            )
        )
    return candidates

def parse_middle_dot_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "middle_dot_numeric":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None

def middle_dot_number_reading(blocks: list[str]) -> str:
    if not blocks:
        return ""
    
    # First block: Sino Korean reading if len <= 2, else digit-by-digit
    first_block = blocks[0]
    if len(first_block) <= 2:
        reading_parts = [number_to_korean_under_10000(int(first_block))]
    else:
        reading_parts = ["".join(SINO_DIGITS[int(d)] for d in first_block)]
    
    # Subsequent blocks: Digit-by-digit reading
    for block in blocks[1:]:
        block_reading = "".join(SINO_DIGITS[int(d)] for d in block)
        reading_parts.append(block_reading)
    
    # Join with space
    return " ".join(reading_parts)

__all__ = ["scan_middle_dot_candidates", "parse_middle_dot_candidate", "middle_dot_number_reading"]
