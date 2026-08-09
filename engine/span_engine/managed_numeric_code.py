from __future__ import annotations

from engine.span_engine.lexicon import (
    CASE_INSENSITIVE_NUMERIC_CODE_READINGS,
    DICTIONARY_READINGS,
)
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.single_letter_code import numeric_code_number_reading

_MAX_INTEGER_SUFFIX_DIGITS = 2
_KOREAN_SUFFIXES = (
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "와",
    "과",
    "도",
    "로",
    "으로",
    "에",
    "에서",
    "부터",
    "까지",
    "입니다",
)


def scan_managed_acronym_numeric_code_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for surface, surface_reading, case_insensitive in _managed_numeric_code_bases():
        haystack = raw_text.casefold() if case_insensitive else raw_text
        needle = surface.casefold() if case_insensitive else surface
        start = haystack.find(needle)
        while start != -1:
            candidate = _candidate_at(raw_text, start, surface, surface_reading)
            if candidate is not None:
                candidates.append(candidate)
            else:
                malformed = _malformed_preserve_candidate_at(raw_text, start, surface)
                if malformed is not None:
                    candidates.append(malformed)
            start = haystack.find(needle, start + 1)
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def parse_managed_acronym_numeric_code_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "managed_acronym_numeric_code":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def parse_managed_acronym_numeric_code_surface(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "managed_acronym_numeric_code":
        return None
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    for surface, surface_reading, case_insensitive in _managed_numeric_code_bases():
        if not _surface_matches(raw, surface, case_insensitive):
            continue
        separator_start = candidate.core_span.start + len(surface)
        hyphen = raw_text[separator_start : separator_start + 1]
        number_start = separator_start + 1 if hyphen == "-" else separator_start
        number = raw_text[number_start : candidate.core_span.end]
        number_reading = numeric_code_number_reading(number)
        if number_reading is None:
            return None
        pieces = [
            RenderPiece(
                text=surface_reading,
                provenance="GENERATED_READING",
                source_span=SourceSpan(candidate.core_span.start, separator_start),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        ]
        if hyphen == "-":
            pieces.append(
                RenderPiece(
                    text="-",
                    provenance="ORIGINAL_BOUNDARY",
                    source_span=SourceSpan(separator_start, number_start),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
        pieces.append(
            RenderPiece(
                text=number_reading if hyphen == "-" else f" {number_reading}",
                provenance="GENERATED_READING",
                source_span=SourceSpan(number_start, candidate.core_span.end),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        return Surface(
            surface_type=candidate.surface_type or "MANAGED_ACRONYM_NUMERIC_CODE_SURFACE",
            owner=candidate.owner,
            raw=raw,
            span=candidate.core_span,
            reading=(
                f"{surface_reading}-{number_reading}"
                if hyphen == "-"
                else f"{surface_reading} {number_reading}"
            ),
            render_pieces=pieces,
            metadata={"reason": candidate.reason},
        )
    return None


def _managed_numeric_code_bases() -> list[tuple[str, str, bool]]:
    return sorted(
        [
            *(
                (surface, reading, False)
                for surface, reading in DICTIONARY_READINGS.items()
                if _is_managed_numeric_code_base(surface)
            ),
            *(
                (surface, reading, True)
                for surface, reading in CASE_INSENSITIVE_NUMERIC_CODE_READINGS.items()
            ),
        ],
        key=lambda item: len(item[0]),
        reverse=True,
    )


def _surface_matches(raw: str, surface: str, case_insensitive: bool) -> bool:
    candidate = raw[: len(surface)]
    return (
        candidate.casefold() == surface.casefold()
        if case_insensitive
        else candidate == surface
    )


def _is_managed_numeric_code_base(surface: str) -> bool:
    if len(surface) <= 1:
        return False
    if not surface[0].isascii() or not surface[0].isalpha():
        return False
    if not surface[-1].isascii() or not surface[-1].isalpha():
        return False
    return all(char.isascii() and (char.isalnum() or char == "-") for char in surface)


def _candidate_at(
    raw_text: str,
    start: int,
    surface: str,
    surface_reading: str,
) -> SurfaceCandidate | None:
    left_end = start + len(surface)
    if not _safe_left_boundary(raw_text, start):
        return None

    number_start = left_end
    if raw_text[number_start : number_start + 1] == "-":
        number_start += 1
    if number_start >= len(raw_text) or not raw_text[number_start].isdigit():
        return None

    number_end = _consume_numeric_code_block(raw_text, number_start)
    if number_end is None:
        return None
    if not _safe_right_boundary(raw_text, number_end):
        return None

    number = raw_text[number_start:number_end]
    number_reading = numeric_code_number_reading(number)
    if number_reading is None:
        return None

    span = SourceSpan(start, number_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="managed_acronym_numeric_code",
        surface_type="MANAGED_ACRONYM_NUMERIC_CODE_SURFACE",
        reason="managed_dictionary_numeric_code_suffix_full_claim",
        metadata={"reading": f"{surface_reading} {number_reading}"},
    )


def _malformed_preserve_candidate_at(
    raw_text: str,
    start: int,
    surface: str,
) -> SurfaceCandidate | None:
    left_end = start + len(surface)
    if not _safe_left_boundary(raw_text, start):
        return None
    if left_end >= len(raw_text):
        return None
    marker = raw_text[left_end]
    if marker not in {"+", "-", "."} and not marker.isdigit():
        return None
    end = _consume_malformed_tail(raw_text, left_end)
    if end <= left_end:
        return None
    span = SourceSpan(start, end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="MALFORMED_MANAGED_ACRONYM_NUMERIC_CODE_PRESERVE",
        reason="malformed_managed_dictionary_numeric_code_blocks_partial_fallback",
    )


def _consume_numeric_code_block(raw_text: str, start: int) -> int | None:
    integer_end = start
    while integer_end < len(raw_text) and raw_text[integer_end].isdigit():
        integer_end += 1
    integer = raw_text[start:integer_end]
    if len(integer) > 1 and integer.startswith("0"):
        return None
    if len(integer) > _MAX_INTEGER_SUFFIX_DIGITS:
        return None
    if raw_text[integer_end : integer_end + 1] != ".":
        return integer_end
    fractional_start = integer_end + 1
    fractional_end = fractional_start
    while fractional_end < len(raw_text) and raw_text[fractional_end].isdigit():
        fractional_end += 1
    if fractional_end == fractional_start:
        return None
    return fractional_end


def _consume_malformed_tail(raw_text: str, start: int) -> int:
    end = start
    while end < len(raw_text):
        char = raw_text[end]
        if char.isascii() and (char.isalnum() or char in {"+", "-", "."}):
            end += 1
            continue
        break
    return end


def _safe_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    prev_char = raw_text[start - 1]
    if prev_char.isspace():
        return True
    return not _is_identifier_neighbor(prev_char)


def _safe_right_boundary(raw_text: str, end: int) -> bool:
    if end >= len(raw_text):
        return True
    next_char = raw_text[end]
    if "\uac00" <= next_char <= "\ud7a3":
        return raw_text.startswith(_KOREAN_SUFFIXES, end)
    return not _is_unsafe_tail(next_char)


def _is_unsafe_tail(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\u3130" <= char <= "\u318f":
        return True
    return char in {"_", "-", "/", ".", "&", "+", "·", "ㆍ", "∙"}


def _is_identifier_neighbor(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\uac00" <= char <= "\ud7a3" or "\u3130" <= char <= "\u318f":
        return True
    return char in {"-", "_", "/", "+", "."}


__all__ = [
    "parse_managed_acronym_numeric_code_candidate",
    "parse_managed_acronym_numeric_code_surface",
    "scan_managed_acronym_numeric_code_candidates",
]
