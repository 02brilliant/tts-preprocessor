from __future__ import annotations

import re

from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_number_text


_PARENTHESIZED_HANGUL_ALIAS_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?P<latin>[A-Za-z]+)"
    r"\((?P<alias>[가-힣]+)\)"
    r"(?:"
    r"(?P<hyphen_number>-\d+(?:\.\d+)?)(?![A-Za-z0-9가-힣ㄱ-ㅎㅏ-ㅣ_./])"
    r"|(?![A-Za-z0-9_./])"
    r")"
)


def scan_parenthesized_hangul_alias_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Use a direct Korean parenthetical alias as an English token's reading.

    The candidate owns the complete ``Latin(한글)`` span, but its core is only
    the Latin token. This lets the final parenthesis filter keep its universal
    deletion policy while the generated alias remains mapped to the Latin
    source token.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    candidates: list[SurfaceCandidate] = []
    for match in _PARENTHESIZED_HANGUL_ALIAS_RE.finditer(raw_text):
        latin = match.group("latin")
        if not latin[0].isupper() and latin.casefold() != "su":
            continue
        latin_span = SourceSpan(match.start("latin"), match.end("latin"))
        alias_span = SourceSpan(match.start("alias"), match.end("alias"))
        full_span = SourceSpan(match.start(), match.end())
        hyphen_number = match.group("hyphen_number")
        number_reading = (
            read_number_text(hyphen_number[1:]) if hyphen_number is not None else None
        )
        if hyphen_number is not None and number_reading is None:
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=latin_span,
                full_span=full_span,
                owner="parenthesized_hangul_alias",
                surface_type="PARENTHESIZED_HANGUL_ALIAS_SURFACE",
                reason="direct_latin_korean_parenthetical_alias",
                metadata={
                    "reading": match.group("alias"),
                    "latin_span": latin_span,
                    "alias_span": alias_span,
                    "hyphen_number": hyphen_number,
                    "number_reading": number_reading,
                },
            )
        )
    return candidates


def parse_parenthesized_hangul_alias_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "parenthesized_hangul_alias":
        return None
    reading = candidate.metadata.get("reading")
    latin_span = candidate.metadata.get("latin_span")
    alias_span = candidate.metadata.get("alias_span")
    hyphen_number = candidate.metadata.get("hyphen_number")
    number_reading = candidate.metadata.get("number_reading")
    if not (
        isinstance(reading, str)
        and isinstance(latin_span, SourceSpan)
        and isinstance(alias_span, SourceSpan)
        and candidate.full_span.start == latin_span.start
        and latin_span.end < alias_span.start < alias_span.end < candidate.full_span.end
    ):
        return None
    if hyphen_number is not None and not (
        isinstance(hyphen_number, str) and isinstance(number_reading, str)
    ):
        return None

    render_pieces = [
        RenderPiece(
            text=reading,
            provenance="GENERATED_READING",
            source_span=latin_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
    ]
    if hyphen_number is not None:
        hyphen_start = alias_span.end + 1
        number_start = hyphen_start + 1
        render_pieces.extend(
            (
                RenderPiece(
                    text="-",
                    provenance="ORIGINAL_BOUNDARY",
                    source_span=SourceSpan(hyphen_start, number_start),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                ),
                RenderPiece(
                    text=number_reading,
                    provenance="GENERATED_READING",
                    source_span=SourceSpan(number_start, candidate.full_span.end),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                ),
            )
        )

    return Surface(
        surface_type=candidate.surface_type or "PARENTHESIZED_HANGUL_ALIAS_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.full_span.start : candidate.full_span.end],
        span=candidate.full_span,
        reading=f"{reading}{hyphen_number or ''}{number_reading or ''}",
        render_pieces=render_pieces,
        metadata={"reason": candidate.reason, "consume_parenthetical_alias": True},
    )


__all__ = [
    "parse_parenthesized_hangul_alias_candidate",
    "scan_parenthesized_hangul_alias_candidates",
]
