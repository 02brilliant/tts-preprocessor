from __future__ import annotations

import re
from dataclasses import dataclass

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_fraction_text
from engine.span_engine.residual_spacing import needs_residual_hangul_space
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    apply_sign_profile,
    parse_sign_surface,
)

_INTEGER_RE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_TEXTUAL_INTEGER_RE = r"[0-9][0-9,]*"
_SLASH_ALIASES = "/／⁄∕"
_MINUS_ALIASES = "-−－"
_FRACTION_RE = re.compile(
    rf"(?P<sign>[{_MINUS_ALIASES}]?)(?P<numerator>{_INTEGER_RE})[{_SLASH_ALIASES}](?P<denominator>{_INTEGER_RE})"
)
_TEXTUAL_FRACTION_RE = re.compile(
    rf"(?P<denominator>{_TEXTUAL_INTEGER_RE})(?P<left_space>[ \t]*)"
    rf"(?P<marker>분의)(?P<right_space>[ \t]*)"
    rf"(?P<numerator>{_TEXTUAL_INTEGER_RE})"
)
_SPACED_FRACTION_RE = re.compile(
    rf"{_INTEGER_RE}\s+[{_SLASH_ALIASES}]|{_INTEGER_RE}[{_SLASH_ALIASES}]\s+"
)
_PREV_BLOCKERS = frozenset("+.,~:/_")
_NEXT_BLOCKERS = frozenset(".,+-~:/_")


@dataclass(frozen=True)
class FractionOperandParse:
    source_span: SourceSpan
    numerator: str
    denominator: str
    sign_surface: str | None
    reading: str


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
        parsed = parse_fraction_operand_at(raw_text, match.start())
        if parsed is None or parsed.source_span.end != match.end():
            candidates.append(_preserve_candidate(span, "fraction_zero_or_invalid_preserve"))
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="fraction",
                surface_type="FRACTION_SURFACE",
                reason="slash_fraction_full_consume_gate",
                metadata={
                    "numerator": parsed.numerator,
                    "denominator": parsed.denominator,
                    "reading": parsed.reading,
                    "sign_profile": SIGNED_OWNER_POLICIES["fraction"].sign_profile.value,
                    "sign_surface": parsed.sign_surface,
                    "numeric_form": "FRACTION",
                },
            )
        )
    return candidates


def scan_textual_fraction_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    """Claim Korean denominator-first fractions such as ``5000분의 1``.

    This owner runs before the time owner so the ``분`` marker cannot be
    mistaken for an unsafe minute suffix and partially preserve the fraction.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _TEXTUAL_FRACTION_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if not _valid_textual_fraction_boundary(raw_text, span):
            continue
        reading = read_fraction_text(
            match.group("numerator"), match.group("denominator")
        )
        metadata = {
            "denominator_span": SourceSpan(
                match.start("denominator"), match.end("denominator")
            ),
            "left_space_span": SourceSpan(
                match.start("left_space"), match.end("left_space")
            ),
            "marker_span": SourceSpan(match.start("marker"), match.end("marker")),
            "right_space_span": SourceSpan(
                match.start("right_space"), match.end("right_space")
            ),
            "numerator_span": SourceSpan(
                match.start("numerator"), match.end("numerator")
            ),
        }
        if reading is None:
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="preserve",
                    surface_type="TEXTUAL_FRACTION_PRESERVE_SURFACE",
                    reason="textual_fraction_invalid_preserve",
                )
            )
            continue
        denominator_reading, numerator_reading = reading.split("분의 ", 1)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="textual_fraction",
                surface_type="TEXTUAL_FRACTION_SURFACE",
                reason="textual_fraction_full_consume_gate",
                metadata={
                    **metadata,
                    "denominator_reading": denominator_reading,
                    "numerator_reading": numerator_reading,
                },
            )
        )
    return candidates


def parse_fraction_operand_at(
    raw_text: str,
    start: int,
) -> FractionOperandParse | None:
    """Parse one existing-policy fraction operand without outer-boundary checks."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(start, int):
        raise TypeError("start must be int")
    if start < 0 or start >= len(raw_text):
        return None
    match = _FRACTION_RE.match(raw_text, start)
    if match is None:
        return None
    numerator = match.group("numerator")
    denominator = match.group("denominator")
    reading = read_fraction_text(numerator, denominator)
    if reading is None:
        return None
    sign_surface = match.group("sign") or None
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
        return None
    return FractionOperandParse(
        source_span=SourceSpan(start, match.end()),
        numerator=numerator,
        denominator=denominator,
        sign_surface=sign_surface,
        reading=reading,
    )


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
    if not isinstance(reading, str):
        return None
    if needs_residual_hangul_space(raw_text, candidate.core_span.end):
        return f"{reading} "
    return reading


def parse_textual_fraction_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "textual_fraction":
        return None
    denominator_reading = candidate.metadata.get("denominator_reading")
    numerator_reading = candidate.metadata.get("numerator_reading")
    denominator_span = candidate.metadata.get("denominator_span")
    left_space_span = candidate.metadata.get("left_space_span")
    marker_span = candidate.metadata.get("marker_span")
    right_space_span = candidate.metadata.get("right_space_span")
    numerator_span = candidate.metadata.get("numerator_span")
    if not (
        isinstance(denominator_reading, str)
        and isinstance(numerator_reading, str)
        and isinstance(denominator_span, SourceSpan)
        and isinstance(left_space_span, SourceSpan)
        and isinstance(marker_span, SourceSpan)
        and isinstance(right_space_span, SourceSpan)
        and isinstance(numerator_span, SourceSpan)
    ):
        return None

    piece_metadata = {"surface_type": candidate.surface_type}
    pieces = [
        RenderPiece(
            text=denominator_reading,
            provenance="GENERATED_READING",
            source_span=denominator_span,
            owner=candidate.owner,
            metadata=piece_metadata,
        )
    ]
    if left_space_span.length:
        pieces.append(
            RenderPiece(
                text=raw_text[left_space_span.start : left_space_span.end],
                provenance="ORIGINAL_SPACE",
                source_span=left_space_span,
                owner=candidate.owner,
                metadata=piece_metadata,
            )
        )
    pieces.append(
        RenderPiece(
            text=raw_text[marker_span.start : marker_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=marker_span,
            owner=candidate.owner,
            metadata=piece_metadata,
        )
    )
    if right_space_span.length:
        pieces.append(
            RenderPiece(
                text=raw_text[right_space_span.start : right_space_span.end],
                provenance="ORIGINAL_SPACE",
                source_span=right_space_span,
                owner=candidate.owner,
                metadata=piece_metadata,
            )
        )
    pieces.append(
        RenderPiece(
            text=numerator_reading,
            provenance="GENERATED_READING",
            source_span=numerator_span,
            owner=candidate.owner,
            metadata=piece_metadata,
        )
    )
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    return Surface(
        surface_type=candidate.surface_type or "TEXTUAL_FRACTION_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading="".join(piece.text for piece in pieces),
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def _valid_textual_fraction_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None and (
        (prev_char.isascii() and prev_char.isalnum())
        or prev_char in "+-.,~:/_·"
    ):
        return False
    if next_char is not None and (
        (next_char.isascii() and next_char.isalnum())
        or next_char in ".+-~:/_·"
    ):
        return False
    return True


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


__all__ = [
    "FractionOperandParse",
    "parse_fraction_candidate",
    "parse_fraction_operand_at",
    "parse_textual_fraction_candidate",
    "scan_fraction_candidates",
    "scan_textual_fraction_candidates",
]
