from __future__ import annotations

from engine.span_engine.counter import HYBRID_COUNTER_THRESHOLD, native_number_under_100
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_text, read_spaced_integer_text
from engine.span_engine.spoken_boundary import join_spoken_numeric_boundary
from engine.span_engine.units import is_free_standing_je_before


_ORDINAL_SUFFIX = "번째"
_SPECIAL_ORDINAL_READINGS = {1: "첫", 2: "두", 3: "세", 4: "네"}


def scan_ordinal_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        candidate = _match_ordinal_candidate(raw_text, index)
        if candidate is not None:
            candidates.append(candidate)
            index = candidate.core_span.end
            continue
        preserve = _match_invalid_ordinal_preserve(raw_text, index)
        if preserve is not None:
            candidates.append(preserve)
            index = preserve.core_span.end
            continue
        index += 1
    return candidates


def parse_ordinal_candidate(raw_text: str, candidate: SurfaceCandidate) -> Surface | None:
    if candidate.owner != "ordinal":
        return None
    reading = candidate.metadata.get("reading")
    number_span = candidate.metadata.get("number_span")
    suffix_span = candidate.metadata.get("suffix_span")
    je_span = candidate.metadata.get("je_span")
    if not (
        isinstance(reading, str)
        and isinstance(number_span, SourceSpan)
        and isinstance(suffix_span, SourceSpan)
        and reading.endswith(_ORDINAL_SUFFIX)
    ):
        return None
    body = reading[2:].lstrip() if isinstance(je_span, SourceSpan) else reading
    if not body.endswith(_ORDINAL_SUFFIX):
        return None
    number_with_boundary = body[: -len(_ORDINAL_SUFFIX)]
    pieces: list[RenderPiece] = []
    if isinstance(je_span, SourceSpan):
        pieces.append(
            RenderPiece(
                text="제",
                provenance="ORIGINAL_KOREAN",
                source_span=je_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        if number_span.start > je_span.end and raw_text[je_span.end:number_span.start] == " ":
            pieces.append(
                RenderPiece(
                    text="-",
                    provenance="GENERATED_PUNCT",
                    source_span=SourceSpan(je_span.end, number_span.start),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
            generated_number = number_with_boundary
        else:
            generated_number = f"-{number_with_boundary}"
    else:
        generated_number = number_with_boundary
    pieces.extend(
        [
            RenderPiece(
                text=generated_number,
                provenance="GENERATED_READING",
                source_span=number_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
            RenderPiece(
                text=_ORDINAL_SUFFIX,
                provenance="ORIGINAL_KOREAN",
                source_span=suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
        ]
    )
    return Surface(
        surface_type=candidate.surface_type or "ORDINAL_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.core_span.start : candidate.core_span.end],
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def ordinal_reading(raw_number: str) -> str | None:
    if not raw_number or not raw_number.isascii():
        return None
    if "." in raw_number:
        sino = read_decimal_text(raw_number)
        return join_spoken_numeric_boundary(sino, _ORDINAL_SUFFIX) if sino is not None else None
    if not raw_number.isdigit():
        return None
    if len(raw_number) > 1 and raw_number.startswith("0"):
        return None
    value = int(raw_number)
    if value < 1:
        return None
    if value in _SPECIAL_ORDINAL_READINGS:
        return join_spoken_numeric_boundary(_SPECIAL_ORDINAL_READINGS[value], _ORDINAL_SUFFIX)
    if value <= HYBRID_COUNTER_THRESHOLD:
        native = native_number_under_100(value)
        if native is not None:
            return join_spoken_numeric_boundary(native, _ORDINAL_SUFFIX)
    sino = read_spaced_integer_text(raw_number)
    return join_spoken_numeric_boundary(sino, _ORDINAL_SUFFIX) if sino is not None else None


def _match_invalid_ordinal_preserve(
    raw_text: str, index: int
) -> SurfaceCandidate | None:
    surface = _ordinal_surface_at(raw_text, index)
    if surface is None:
        return None
    number_start, number_end, suffix_start, suffix_end, je_span = surface
    raw_number = raw_text[number_start:number_end]
    if ordinal_reading(raw_number) is not None:
        return None
    claim_start = je_span.start if je_span is not None else number_start
    span = SourceSpan(claim_start, suffix_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="ORDINAL_PRESERVE_SURFACE",
        reason="invalid_ordinal_surface",
    )


def _match_ordinal_candidate(raw_text: str, index: int) -> SurfaceCandidate | None:
    surface = _ordinal_surface_at(raw_text, index)
    if surface is None:
        return None
    number_start, number_end, suffix_start, suffix_end, je_span = surface
    raw_number = raw_text[number_start:number_end]
    reading = ordinal_reading(raw_number)
    if reading is None:
        return None
    claim_start = je_span.start if je_span is not None else number_start
    full_reading = f"제-{reading}" if je_span is not None else reading
    span = SourceSpan(claim_start, suffix_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="ordinal",
        surface_type="ORDINAL_SURFACE",
        reason="hybrid_native_sino_ordinal_full_claim",
        metadata={
            "reading": full_reading,
            "number_span": SourceSpan(number_start, number_end),
            "suffix_span": SourceSpan(suffix_start, suffix_end),
            "je_span": je_span,
        },
    )


def _ordinal_surface_at(
    raw_text: str, index: int
) -> tuple[int, int, int, int, SourceSpan | None] | None:
    pos = index
    je_span: SourceSpan | None = None
    if raw_text.startswith("제", pos):
        if pos > 0 and not raw_text[pos - 1].isspace():
            return None
        je_span = SourceSpan(pos, pos + 1)
        pos += 1
        pos = _consume_optional_ascii_space(raw_text, pos)
    elif pos > 0 and raw_text[pos - 1] == "제":
        if not is_free_standing_je_before(raw_text, pos):
            return None
        je_span = SourceSpan(pos - 1, pos)
    if not _valid_number_left_boundary(raw_text, pos):
        return None
    number_start = pos
    number_end = _consume_ordinal_number(raw_text, pos)
    if number_end is None:
        return None
    suffix_start = _consume_optional_ascii_space(raw_text, number_end)
    if not raw_text.startswith(_ORDINAL_SUFFIX, suffix_start):
        return None
    suffix_end = suffix_start + len(_ORDINAL_SUFFIX)
    return number_start, number_end, suffix_start, suffix_end, je_span


def _consume_ordinal_number(raw_text: str, start: int) -> int | None:
    index = start
    digit_end = _consume_digits(raw_text, index)
    if digit_end == index:
        return None
    index = digit_end
    if index < len(raw_text) and raw_text[index] == ".":
        fraction_start = index + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        index = fraction_end
    number = raw_text[start:index]
    if "." in number:
        integer_part, _, fractional_part = number.partition(".")
        if not integer_part.isdigit() or not fractional_part.isdigit():
            return None
        if len(integer_part) > 1 and integer_part.startswith("0"):
            return None
        return index
    if len(number) > 1 and number.startswith("0"):
        return None
    return index


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _valid_number_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    previous = raw_text[start - 1]
    if previous.isspace():
        return True
    if previous.isascii() and previous.isalnum():
        return False
    if previous == "제":
        return is_free_standing_je_before(raw_text, start)
    if "\uac00" <= previous <= "\ud7a3":
        return False
    return previous not in {"_", "/", ".", ",", "~", "+", "-"}


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


__all__ = ["ordinal_reading", "parse_ordinal_candidate", "scan_ordinal_candidates"]
