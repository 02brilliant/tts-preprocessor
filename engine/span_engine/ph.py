from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.number import number_to_korean_under_10000

_PH_RE = re.compile(r"pH\s*\d+(?:\.\d+)?")
_DIGIT_READINGS = {
    "0": "영",
    "1": "일",
    "2": "이",
    "3": "삼",
    "4": "사",
    "5": "오",
    "6": "육",
    "7": "칠",
    "8": "팔",
    "9": "구",
}


def scan_ph_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _PH_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        full_span = SourceSpan(match.start(), _ph_like_token_end(raw_text, match.end()))
        if not _valid_ph_boundary(raw_text, full_span):
            candidates.append(_preserve_candidate(full_span, "ph_invalid_boundary_preserve"))
            continue
        if full_span.end != match.end():
            candidates.append(_preserve_candidate(full_span, "ph_unsafe_tail_preserve"))
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="ph",
                surface_type="PH_SURFACE",
                reason="ph_numeric_full_consume",
                metadata={"reading": _reading(match.group(0))},
            )
        )
    return candidates


def parse_ph_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "ph":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _reading(raw: str) -> str:
    number = raw[2:].strip()
    return f"피에이치 {_number_reading(number)}"


def _number_reading(number: str) -> str:
    integer_part, dot, fraction_part = number.partition(".")
    integer = number_to_korean_under_10000(int(integer_part))
    if not dot:
        return integer
    return f"{integer}쩜{''.join(_DIGIT_READINGS[digit] for digit in fraction_part)}"


def _valid_ph_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None and (prev_char.isascii() and prev_char.isalnum()):
        return False
    if prev_char is not None and "\uac00" <= prev_char <= "\ud7a3":
        return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    return True


def _ph_like_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if char.isascii() and char.isalnum():
            index += 1
            continue
        if char == ".":
            index += 1
            continue
        break
    return index


def _preserve_candidate(span: SourceSpan, reason: str) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="PH_PRESERVE_SURFACE",
        reason=reason,
    )


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = ["parse_ph_candidate", "scan_ph_candidates"]
