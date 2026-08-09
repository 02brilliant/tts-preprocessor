from __future__ import annotations

from engine.span_engine.counter import HYBRID_COUNTER_THRESHOLD, native_number_under_100
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_spaced_integer_text


_ORDINAL_SUFFIX = "번째"
_SPECIAL_ORDINAL_READINGS = {1: "첫", 2: "두", 3: "세", 4: "네"}


def scan_ordinal_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]) or not _valid_left_boundary(raw_text, index):
            index += 1
            continue
        number_end = _consume_digits(raw_text, index)
        if not raw_text.startswith(_ORDINAL_SUFFIX, number_end):
            index = number_end
            continue
        full_end = number_end + len(_ORDINAL_SUFFIX)
        if not _valid_right_boundary(raw_text, full_end):
            index = full_end
            continue
        raw_number = raw_text[index:number_end]
        reading = ordinal_reading(raw_number)
        if reading is not None:
            span = SourceSpan(index, full_end)
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="ordinal",
                    surface_type="ORDINAL_SURFACE",
                    reason="hybrid_native_sino_ordinal_full_claim",
                    metadata={
                        "reading": reading,
                        "number_span": SourceSpan(index, number_end),
                        "suffix_span": SourceSpan(number_end, full_end),
                    },
                )
            )
        index = full_end
    return candidates


def parse_ordinal_candidate(raw_text: str, candidate: SurfaceCandidate) -> Surface | None:
    if candidate.owner != "ordinal":
        return None
    reading = candidate.metadata.get("reading")
    number_span = candidate.metadata.get("number_span")
    suffix_span = candidate.metadata.get("suffix_span")
    if not (
        isinstance(reading, str)
        and isinstance(number_span, SourceSpan)
        and isinstance(suffix_span, SourceSpan)
        and reading.endswith(_ORDINAL_SUFFIX)
    ):
        return None
    prefix = reading[: -len(_ORDINAL_SUFFIX)]
    pieces = [
        RenderPiece(
            text=prefix,
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
    if not raw_number or not raw_number.isascii() or not raw_number.isdigit():
        return None
    if len(raw_number) > 1 and raw_number.startswith("0"):
        return None
    value = int(raw_number)
    if value < 1:
        return None
    if value in _SPECIAL_ORDINAL_READINGS:
        return f"{_SPECIAL_ORDINAL_READINGS[value]} 번째"
    if value <= HYBRID_COUNTER_THRESHOLD:
        native = native_number_under_100(value)
        if native is not None:
            return f"{native} 번째"
    sino = read_spaced_integer_text(raw_number)
    return f"{sino} 번째" if sino is not None else None


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _valid_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    previous = raw_text[start - 1]
    return not (
        previous.isascii() and previous.isalnum()
    ) and previous not in {"_", "/", ".", ",", "~", "+", "-"}


def _valid_right_boundary(raw_text: str, end: int) -> bool:
    if end == len(raw_text):
        return True
    following = raw_text[end]
    return not (following.isascii() and following.isalnum()) and following not in {
        "_",
        "/",
        ".",
        "-",
    }


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


__all__ = ["ordinal_reading", "parse_ordinal_candidate", "scan_ordinal_candidates"]
