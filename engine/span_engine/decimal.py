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
from engine.span_engine.sign_aliases import is_signed_numeric_sign
from engine.span_engine.span_guards import (
    is_decimal_like_url_or_path_context,
    span_overlaps_excluded_ranges,
)

_DECIMAL_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\.(\d+)")
_SAFE_DECIMAL_ATTACHED_PARTICLES = ("으로", "로")

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
            if _starts_with_blocking_korean_suffix(raw_text, span.end):
                # This is 3.5가, preserve it.
                continue
        
        # Check for URL context (e.g., http://x/12.3)
        if is_decimal_like_url_or_path_context(raw_text, span):
            continue

        if _is_leading_zero_malformed_decimal_integer(left):
            preserve_candidate = _leading_zero_malformed_decimal_preserve_candidate(
                raw_text, span, prev_char
            )
            if preserve_candidate is not None:
                candidates.append(preserve_candidate)
            continue

        integer_reading = read_integer_text(left)
        if integer_reading is None and "," not in left and left.isascii() and left.isdigit():
            if _has_attached_hangul_tail(raw_text, span.end):
                continue
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


def _starts_with_blocking_korean_suffix(raw_text: str, index: int) -> bool:
    suffix = raw_text[index:]
    for blocking_suffix in ("가", "호", "동", "번", "길", "번지"):
        if suffix.startswith(blocking_suffix):
            return True
    if suffix.startswith("로") and _safe_decimal_particle_span(raw_text, index) is None:
        return True
    return False


def _safe_decimal_particle_span(raw_text: str, index: int) -> SourceSpan | None:
    for particle in _SAFE_DECIMAL_ATTACHED_PARTICLES:
        if not raw_text.startswith(particle, index):
            continue
        end = index + len(particle)
        if _valid_after_attached_particle(raw_text, end):
            return SourceSpan(index, end)
    return None


def _valid_after_attached_particle(raw_text: str, index: int) -> bool:
    if index >= len(raw_text):
        return True
    char = raw_text[index]
    if char.isspace():
        return True
    if char in {".", ",", "!", "?", ";", ":", ")", "]", "}"}:
        return True
    return False


def _has_attached_hangul_tail(raw_text: str, index: int) -> bool:
    if index >= len(raw_text):
        return False
    char = raw_text[index]
    return "\uac00" <= char <= "\ud7a3"


def _is_leading_zero_malformed_decimal_integer(left: str) -> bool:
    if "," in left:
        return False
    if not left.isascii() or not left.isdigit():
        return False
    return len(left) >= 2 and left.startswith("0")


def _leading_zero_malformed_decimal_preserve_candidate(
    raw_text: str, decimal_span: SourceSpan, prev_char: str | None
) -> SurfaceCandidate | None:
    preserve_start = decimal_span.start
    if prev_char is not None and is_signed_numeric_sign(prev_char):
        preserve_start = decimal_span.start - 1
    full_span = SourceSpan(preserve_start, decimal_span.end)
    return SurfaceCandidate(
        core_span=full_span,
        full_span=full_span,
        owner="preserve",
        surface_type="LEADING_ZERO_MALFORMED_DECIMAL_PRESERVE_SURFACE",
        reason="leading_zero_malformed_decimal_preserve",
    )


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
