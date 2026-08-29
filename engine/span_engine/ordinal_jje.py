from __future__ import annotations

from engine.span_engine.counter import HYBRID_COUNTER_THRESHOLD, native_number_under_100
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_spaced_integer_text
from engine.span_engine.units import is_free_standing_je_before


_ORDINAL_JJE_SUFFIX = "째"
_SPECIAL = {1: "첫", 2: "둘", 3: "셋", 4: "넷"}
_RANGE_DELIMITERS = frozenset("~∼～〜-–—")


def scan_ordinal_jje_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        candidate = _match_ordinal_jje_candidate(raw_text, index)
        if candidate is not None:
            candidates.append(candidate)
            index = candidate.core_span.end
            continue
        preserve = _match_invalid_ordinal_jje_preserve(raw_text, index)
        if preserve is not None:
            candidates.append(preserve)
            index = preserve.core_span.end
            continue
        index += 1
    return candidates


def parse_ordinal_jje_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "ordinal_jje":
        return None
    stem_reading = candidate.metadata.get("stem_reading")
    number_span = candidate.metadata.get("number_span")
    suffix_span = candidate.metadata.get("suffix_span")
    je_span = candidate.metadata.get("je_span")
    if not (
        isinstance(stem_reading, str)
        and isinstance(number_span, SourceSpan)
        and isinstance(suffix_span, SourceSpan)
    ):
        return None

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
        if number_span.start > je_span.end:
            pieces.append(
                RenderPiece(
                    text=" ",
                    provenance="ORIGINAL_SPACE",
                    source_span=SourceSpan(je_span.end, number_span.start),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
        else:
            pieces.append(
                RenderPiece(
                    text=" ",
                    provenance="GENERATED_READING",
                    source_span=je_span,
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
    pieces.extend(
        [
            RenderPiece(
                text=stem_reading,
                provenance="GENERATED_READING",
                source_span=number_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
            RenderPiece(
                text=_ORDINAL_JJE_SUFFIX,
                provenance="ORIGINAL_KOREAN",
                source_span=suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
        ]
    )
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    return Surface(
        surface_type=candidate.surface_type or "ORDINAL_JJE_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading="".join(piece.text for piece in pieces),
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def ordinal_jje_reading(raw_number: str) -> str | None:
    if not raw_number or not raw_number.isascii() or not raw_number.isdigit():
        return None
    if len(raw_number) > 1 and raw_number.startswith("0"):
        return None
    value = int(raw_number)
    if value < 1:
        return None
    if value in _SPECIAL:
        return f"{_SPECIAL[value]}{_ORDINAL_JJE_SUFFIX}"
    if value <= HYBRID_COUNTER_THRESHOLD:
        native = native_number_under_100(value)
        if native is not None:
            return f"{native}{_ORDINAL_JJE_SUFFIX}"
    sino = read_spaced_integer_text(raw_number)
    return f"{sino}{_ORDINAL_JJE_SUFFIX}" if sino is not None else None


def _match_ordinal_jje_candidate(
    raw_text: str, index: int
) -> SurfaceCandidate | None:
    surface = _ordinal_jje_surface_at(raw_text, index)
    if surface is None:
        return None
    number_start, number_end, suffix_start, suffix_end, je_span = surface
    raw_number = raw_text[number_start:number_end]
    reading = ordinal_jje_reading(raw_number)
    if reading is None:
        return None
    stem_reading = reading[: -len(_ORDINAL_JJE_SUFFIX)]
    claim_start = je_span.start if je_span is not None else number_start
    span = SourceSpan(claim_start, suffix_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="ordinal_jje",
        surface_type="ORDINAL_JJE_SURFACE",
        reason="hybrid_native_sino_ordinal_jje_full_claim",
        metadata={
            "stem_reading": stem_reading,
            "number_span": SourceSpan(number_start, number_end),
            "suffix_span": SourceSpan(suffix_start, suffix_end),
            "je_span": je_span,
        },
    )


def _match_invalid_ordinal_jje_preserve(
    raw_text: str, index: int
) -> SurfaceCandidate | None:
    surface = _ordinal_jje_surface_at(raw_text, index)
    if surface is None:
        return None
    number_start, number_end, _, suffix_end, je_span = surface
    if ordinal_jje_reading(raw_text[number_start:number_end]) is not None:
        return None
    claim_start = je_span.start if je_span is not None else number_start
    span = SourceSpan(claim_start, suffix_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="ORDINAL_JJE_PRESERVE_SURFACE",
        reason="invalid_ordinal_jje_surface",
    )


def _ordinal_jje_surface_at(
    raw_text: str, index: int
) -> tuple[int, int, int, int, SourceSpan | None] | None:
    pos = index
    je_span: SourceSpan | None = None
    if raw_text.startswith("제", pos):
        if pos > 0 and not raw_text[pos - 1].isspace():
            return None
        je_span = SourceSpan(pos, pos + 1)
        pos = _consume_optional_ascii_space(raw_text, pos + 1)
    elif pos > 0 and raw_text[pos - 1] == "제":
        if not is_free_standing_je_before(raw_text, pos):
            return None
        je_span = SourceSpan(pos - 1, pos)
    if not _valid_number_left_boundary(raw_text, pos):
        return None
    number_start = pos
    number_end = _consume_number(raw_text, pos)
    if number_end is None:
        return None
    suffix_start = _consume_optional_ascii_space(raw_text, number_end)
    if not raw_text.startswith(_ORDINAL_JJE_SUFFIX, suffix_start):
        return None
    return (
        number_start,
        number_end,
        suffix_start,
        suffix_start + len(_ORDINAL_JJE_SUFFIX),
        je_span,
    )


def _consume_number(raw_text: str, start: int) -> int | None:
    end = _consume_digits(raw_text, start)
    if end == start:
        return None
    if end < len(raw_text) and raw_text[end] == ".":
        fractional_end = _consume_digits(raw_text, end + 1)
        if fractional_end == end + 1:
            return None
        return fractional_end
    return end


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isascii() and raw_text[index].isdigit():
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
    if previous in _RANGE_DELIMITERS:
        return False
    if "\uac00" <= previous <= "\ud7a3":
        return False
    return previous not in {"_", "/", ".", ",", "+"}


__all__ = [
    "ordinal_jje_reading",
    "parse_ordinal_jje_candidate",
    "scan_ordinal_jje_candidates",
]
