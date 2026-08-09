from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.number import SINO_DIGITS
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
            equipment_sequence = raw_text.startswith("호기", span.end)
            if not equipment_sequence and any(
                raw_text[span.end:].startswith(s)
                for s in ("가", "호", "동", "번", "로", "길", "번지")
            ):
                continue
        else:
            equipment_sequence = False

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
                metadata={
                    "reading": reading,
                    "blocks": blocks,
                    "equipment_sequence": equipment_sequence,
                },
            )
        )
    return candidates


def scan_middle_dot_korean_suffix_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    """Return middle-dot numeric blocks that must precede numeric suffix owners."""
    return [
        candidate
        for candidate in scan_middle_dot_candidates(raw_text, excluded_ranges)
        if any(raw_text.startswith(suffix, candidate.core_span.end) for suffix in ("분기", "월", "일"))
    ]

def parse_middle_dot_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "middle_dot_numeric":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None

def middle_dot_number_reading(blocks: list[str]) -> str:
    if not blocks:
        return ""
    
    # Every block is a code-like digit sequence.  In particular, ``12·3``
    # renders as ``일이·삼`` rather than treating the first block as the
    # numeric value 십이.
    reading_parts = [
        "".join(SINO_DIGITS[int(digit)] for digit in block)
        for block in blocks
    ]
    
    # Preserve the source middle-dot structure while reading every numeric
    # block.  A numeric middle dot is a delimiter, not a request to elide the
    # delimiter into whitespace.
    return "·".join(reading_parts)

__all__ = [
    "scan_middle_dot_candidates",
    "scan_middle_dot_korean_suffix_candidates",
    "parse_middle_dot_candidate",
    "middle_dot_number_reading",
]
