from __future__ import annotations

import re

from engine.span_engine.large_unit import (
    MixedIntegerCoreParse,
    parse_large_unit_integer_core_at,
    parse_mixed_integer_core_at,
)
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    read_decimal_fraction_digits,
    read_spaced_integer_text,
)

_KOREAN_NUMERIC_UNIT_CHARS = frozenset("십백천만억조경")
_LEFT_BOUNDARY_BLOCKERS = frozenset("+-.,~:/_")
_RIGHT_BOUNDARY_BLOCKERS = frozenset("+-~:/_")
_CURRENCY_MARKER_CHARS = frozenset("$€£¥₩￦￥＄﹩")
_TRAILING_TOKEN_BLOCKERS = frozenset("/\\_=")
_INTEGER_BLOCK_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")


def scan_mixed_integer_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Claim complete Arabic-Hangul integer cores missed by narrower owners."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue

        parsed, core_kind = _parse_longest_mixed_core(raw_text, index)
        if parsed is None:
            index += 1
            continue

        fraction_span = _mixed_decimal_fraction_span(raw_text, parsed.end)
        span = SourceSpan(
            index,
            fraction_span.end if fraction_span is not None else parsed.end,
        )
        if not is_safe_mixed_integer_boundary(raw_text, span):
            if fraction_span is not None:
                preserve_span = _mixed_decimal_preserve_span(raw_text, span)
                candidates.append(
                    SurfaceCandidate(
                        core_span=preserve_span,
                        full_span=preserve_span,
                        owner="preserve",
                        surface_type="INVALID_MIXED_DECIMAL_PRESERVE_SURFACE",
                        reason="invalid_or_code_like_mixed_decimal_preserve",
                    )
                )
                index = span.end
                continue
            index += 1
            continue

        reading = parsed.reading
        owner = "mixed_integer_atomic"
        surface_type = "MIXED_INTEGER_SURFACE"
        reason = f"mixed_integer_{core_kind}_full_consume"
        if fraction_span is not None:
            fraction_digits = raw_text[fraction_span.start : fraction_span.end]
            reading = (
                f"{reading}쩜{read_decimal_fraction_digits(fraction_digits)}"
            )
            owner = "mixed_decimal_atomic"
            surface_type = "MIXED_DECIMAL_SURFACE"
            reason = f"mixed_integer_{core_kind}_decimal_full_consume"

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner=owner,
                surface_type=surface_type,
                reason=reason,
                metadata={
                    "reading": reading,
                    "integer_value": parsed.value,
                    "integer_core_end": parsed.end,
                    "fraction_span": fraction_span,
                    "numeric_core_kind": core_kind,
                },
            )
        )
        index = parsed.end
    return candidates


def parse_mixed_integer_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner not in {"mixed_integer_atomic", "mixed_decimal_atomic"}:
        return None
    expected_reading = candidate.metadata.get("reading")
    if not isinstance(expected_reading, str):
        return None
    integer_core_end = candidate.metadata.get("integer_core_end")
    if not isinstance(integer_core_end, int):
        integer_core_end = candidate.core_span.end
    if (
        integer_core_end <= candidate.core_span.start
        or integer_core_end > candidate.core_span.end
    ):
        return None
    fraction_span = candidate.metadata.get("fraction_span")
    if fraction_span is not None and not isinstance(fraction_span, SourceSpan):
        return None

    pieces: list[RenderPiece] = []
    cursor = candidate.core_span.start
    for match in _INTEGER_BLOCK_RE.finditer(
        raw_text, candidate.core_span.start, integer_core_end
    ):
        if cursor < match.start():
            literal_span = SourceSpan(cursor, match.start())
            pieces.append(
                RenderPiece(
                    text=raw_text[literal_span.start : literal_span.end],
                    provenance="ORIGINAL_KOREAN",
                    source_span=literal_span,
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
        number_span = SourceSpan(match.start(), match.end())
        number_reading = read_spaced_integer_text(match.group(0))
        if number_reading is None:
            return None
        pieces.append(
            RenderPiece(
                text=number_reading,
                provenance="GENERATED_READING",
                source_span=number_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        cursor = match.end()
    if cursor < integer_core_end:
        literal_span = SourceSpan(cursor, integer_core_end)
        pieces.append(
            RenderPiece(
                text=raw_text[literal_span.start : literal_span.end],
                provenance="ORIGINAL_KOREAN",
                source_span=literal_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    if fraction_span is not None:
        if (
            integer_core_end >= candidate.core_span.end
            or raw_text[integer_core_end] != "."
            or fraction_span.start != integer_core_end + 1
            or fraction_span.end != candidate.core_span.end
        ):
            return None
        fraction_digits = raw_text[fraction_span.start : fraction_span.end]
        pieces.append(
            RenderPiece(
                text=f"쩜{read_decimal_fraction_digits(fraction_digits)}",
                provenance="GENERATED_READING",
                source_span=SourceSpan(integer_core_end, fraction_span.end),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    if "".join(piece.text for piece in pieces) != expected_reading:
        return None
    return Surface(
        surface_type=candidate.surface_type or "MIXED_INTEGER_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.core_span.start : candidate.core_span.end],
        span=candidate.core_span,
        reading=expected_reading,
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def is_safe_mixed_integer_left_boundary(raw_text: str, start: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(start, int):
        raise TypeError("start must be int")
    if start < 0 or start > len(raw_text):
        return False
    if start == 0:
        return True

    prev_char = raw_text[start - 1]
    if prev_char in _KOREAN_NUMERIC_UNIT_CHARS or prev_char == "제":
        return False
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if (
        prev_char in _LEFT_BOUNDARY_BLOCKERS
        or prev_char in _CURRENCY_MARKER_CHARS
    ):
        return False

    token_start, _ = _mixed_token_bounds(raw_text, start, start)
    if (
        token_start > 0
        and raw_text[token_start - 1]
        in (_LEFT_BOUNDARY_BLOCKERS | _CURRENCY_MARKER_CHARS)
    ):
        return False
    return not _contains_ascii_identifier(raw_text[token_start:start])


def is_safe_mixed_integer_boundary(raw_text: str, span: SourceSpan) -> bool:
    if not is_safe_mixed_integer_left_boundary(raw_text, span.start):
        return False

    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char in _KOREAN_NUMERIC_UNIT_CHARS:
        return False
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in _RIGHT_BOUNDARY_BLOCKERS:
        return False
    if next_char in {",", "."} and (
        span.end + 1 < len(raw_text)
        and _is_ascii_digit(raw_text[span.end + 1])
    ):
        return False

    token_start, token_end = _mixed_token_bounds(raw_text, span.start, span.end)
    if (
        token_end < len(raw_text)
        and raw_text[token_end] in _TRAILING_TOKEN_BLOCKERS
    ):
        return False
    return not _contains_ascii_identifier(raw_text[token_start:token_end])


def _parse_longest_mixed_core(
    raw_text: str, start: int
) -> tuple[MixedIntegerCoreParse | None, str]:
    parsed_candidates = (
        (parse_large_unit_integer_core_at(raw_text, start), "large_unit"),
        (parse_mixed_integer_core_at(raw_text, start), "small_unit"),
    )
    valid = [
        (parsed, core_kind)
        for parsed, core_kind in parsed_candidates
        if parsed is not None
    ]
    if not valid:
        return None, ""
    return max(valid, key=lambda item: item[0].end)


def _mixed_decimal_fraction_span(
    raw_text: str, integer_core_end: int
) -> SourceSpan | None:
    if (
        integer_core_end <= 0
        or integer_core_end >= len(raw_text)
        or not _is_ascii_digit(raw_text[integer_core_end - 1])
        or raw_text[integer_core_end] != "."
    ):
        return None
    fraction_start = integer_core_end + 1
    fraction_end = fraction_start
    while (
        fraction_end < len(raw_text)
        and _is_ascii_digit(raw_text[fraction_end])
    ):
        fraction_end += 1
    if fraction_end == fraction_start:
        return None
    return SourceSpan(fraction_start, fraction_end)


def _mixed_decimal_preserve_span(
    raw_text: str, decimal_span: SourceSpan
) -> SourceSpan:
    token_start, token_end = _mixed_token_bounds(
        raw_text, decimal_span.start, decimal_span.end
    )
    return SourceSpan(token_start, token_end)


def _mixed_token_bounds(raw_text: str, start: int, end: int) -> tuple[int, int]:
    token_start = start
    while token_start > 0 and _is_mixed_token_char(raw_text[token_start - 1]):
        token_start -= 1
    token_end = end
    while token_end < len(raw_text) and _is_mixed_token_char(raw_text[token_end]):
        token_end += 1
    return token_start, token_end


def _is_mixed_token_char(char: str) -> bool:
    return char == "_" or char.isalnum()


def _contains_ascii_identifier(text: str) -> bool:
    return "_" in text or any(
        char.isascii() and char.isalpha() for char in text
    )


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


__all__ = [
    "is_safe_mixed_integer_boundary",
    "is_safe_mixed_integer_left_boundary",
    "parse_mixed_integer_candidate",
    "scan_mixed_integer_candidates",
]
