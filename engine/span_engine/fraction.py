from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_fraction_text
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    apply_sign_profile,
    parse_sign_surface,
)

_INTEGER_RE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_SLASH_ALIASES = "/／⁄∕"
_MINUS_ALIASES = "-−－"
_FRACTION_RE = re.compile(
    rf"(?P<sign>[{_MINUS_ALIASES}]?)(?P<numerator>{_INTEGER_RE})[{_SLASH_ALIASES}](?P<denominator>{_INTEGER_RE})"
)
_SPACED_FRACTION_RE = re.compile(
    rf"{_INTEGER_RE}\s+[{_SLASH_ALIASES}]|{_INTEGER_RE}[{_SLASH_ALIASES}]\s+"
)
_PREV_BLOCKERS = frozenset("+.,~:/_")
_NEXT_BLOCKERS = frozenset(".,+-~:/_")


def scan_fraction_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _SPACED_FRACTION_RE.finditer(raw_text):
        end = _spaced_fraction_token_end(raw_text, match.end())
        span = SourceSpan(match.start(), end)
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        candidates.append(_preserve_candidate(span, "spaced_fraction_preserve"))
    for match in _FRACTION_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if not _valid_boundary(raw_text, span):
            continue
        numerator = match.group("numerator")
        denominator = match.group("denominator")
        reading = read_fraction_text(numerator, denominator)
        if reading is None:
            candidates.append(_preserve_candidate(span, "fraction_zero_or_invalid_preserve"))
            continue
        sign_surface = match.group("sign")
        policy = SIGNED_OWNER_POLICIES["fraction"]
        sign_kind = parse_sign_surface(
            sign_surface,
            minus_aliases=policy.minus_aliases,
        )
        reading = apply_sign_profile(
            reading,
            sign_kind,
            sign_profile=policy.sign_profile,
        )
        if reading is None:
            candidates.append(_preserve_candidate(span, "fraction_sign_invalid_preserve"))
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="fraction",
                surface_type="FRACTION_SURFACE",
                reason="slash_fraction_full_consume_gate",
                metadata={
                    "numerator": numerator,
                    "denominator": denominator,
                    "reading": reading,
                    "sign_profile": policy.sign_profile.value,
                    "sign_surface": sign_surface or None,
                    "numeric_form": "FRACTION",
                },
            )
        )
    return candidates


def _spaced_fraction_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isspace():
        index += 1
    while index < len(raw_text) and raw_text[index].isascii() and raw_text[index].isdigit():
        index += 1
    return index


def parse_fraction_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "fraction":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


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
    if "\uac00" <= next_char <= "\ud7a3":
        return True
    if next_char in _NEXT_BLOCKERS and next_char != ",":
        return False
    return True


def _preserve_candidate(span: SourceSpan, reason: str) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="FRACTION_PRESERVE_SURFACE",
        reason=reason,
    )


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = ["parse_fraction_candidate", "scan_fraction_candidates"]
