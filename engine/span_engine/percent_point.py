from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_fraction_text, read_number_text
from engine.span_engine.sign_aliases import MINUS_SIGN_ALIASES, PLUS_SIGN

_INTEGER_RE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_DECIMAL_RE = rf"{_INTEGER_RE}\.\d+"
_SLASH_ALIASES = "/／"
_MINUS_ALIAS_CLASS = re.escape("".join(sorted(MINUS_SIGN_ALIASES)))
_PERCENT_ALIASES = "%％﹪"
_FRACTION_RE = rf"{_INTEGER_RE}[{_SLASH_ALIASES}]{_INTEGER_RE}"
_NUMBER_RE = rf"(?:{_FRACTION_RE}|{_DECIMAL_RE}|{_INTEGER_RE})"
_PERCENT_POINT_RE = re.compile(
    rf"(?P<sign>[{PLUS_SIGN}{_MINUS_ALIAS_CLASS}]?)(?P<number>{_NUMBER_RE})[{_PERCENT_ALIASES}][pP]"
)
_PREV_BLOCKERS = frozenset("+.,~:/_")


def scan_percent_point_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _PERCENT_POINT_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if not _valid_boundary(raw_text, span):
            continue
        number = match.group("number")
        reading = _read_amount(number)
        if reading is None:
            candidates.append(_preserve_candidate(span, "percent_point_number_invalid_preserve"))
            continue
        if match.group("sign") == PLUS_SIGN:
            reading = f"플러스 {reading}"
        elif match.group("sign"):
            reading = f"마이너스 {reading}"
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="percent_point",
                surface_type="PERCENT_POINT_SURFACE",
                reason="percent_point_full_consume_gate",
                metadata={"number": number, "reading": f"{reading} 퍼센트포인트"},
            )
        )
    return candidates


def parse_percent_point_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "percent_point":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def _read_amount(number: str) -> str | None:
    for slash in _SLASH_ALIASES:
        if slash in number:
            numerator, denominator = number.split(slash, 1)
            return read_fraction_text(numerator, denominator)
    return read_number_text(number)


def _valid_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
        if prev_char == "-" and raw_text[span.start] != "-":
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    return True


def _preserve_candidate(span: SourceSpan, reason: str) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="PERCENT_POINT_PRESERVE_SURFACE",
        reason=reason,
    )


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = ["parse_percent_point_candidate", "scan_percent_point_candidates"]
