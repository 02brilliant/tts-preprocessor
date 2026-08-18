from __future__ import annotations

from engine.span_engine.counter import SUPPORTED_COUNTERS
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import (
    read_number_text,
    read_sino_time_suffix_number_text,
)

ORDINAL_ONLY_SUFFIXES = frozenset({"차", "과"})
PREFIXED_ONLY_EXTRA_SUFFIXES = frozenset(
    {"조", "번", "부", "단", "등", "쪽", "자"}
)
SOURCE_SPACED_PREFIXED_SUFFIXES = frozenset({"조"})
SPACED_UNPREFIXED_NUMERIC_SUFFIXES = frozenset({"시리즈"})
ORDINAL_SUFFIXES = (
    frozenset(SUPPORTED_COUNTERS)
    | ORDINAL_ONLY_SUFFIXES
    | PREFIXED_ONLY_EXTRA_SUFFIXES
)
NON_PREFIXED_NUMERIC_SUFFIXES = frozenset({"초", "선", "분기", "시리즈"})
NUMERIC_SUFFIXES = NON_PREFIXED_NUMERIC_SUFFIXES | ORDINAL_SUFFIXES
PREFIXED_ONLY_SUFFIXES = ORDINAL_SUFFIXES - NON_PREFIXED_NUMERIC_SUFFIXES
_ORDERED_SUFFIXES = sorted(NUMERIC_SUFFIXES, key=len, reverse=True)
_PREV_BLOCKERS = frozenset("+-.,~:/_")


def scan_numeric_suffix_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_digit(raw_text[index]):
            index += 1
            continue
        number_start = index
        number_end = _consume_number(raw_text, number_start)
        if number_end is None:
            index += 1
            continue
        ordinal_prefix_span = _ordinal_prefix_span(raw_text, number_start)
        suffix_start = _consume_optional_ascii_space(raw_text, number_end)
        matched_suffix = False
        for suffix in _ORDERED_SUFFIXES:
            suffix_start = _suffix_start_for_match(
                raw_text, number_end, suffix, ordinal_prefix_span
            )
            if not raw_text.startswith(suffix, suffix_start):
                continue
            matched_suffix = True
            prev_char = raw_text[number_start - 1] if number_start > 0 else None
            if suffix in PREFIXED_ONLY_SUFFIXES and ordinal_prefix_span is None:
                continue
            suffix_end = suffix_start + len(suffix)
            number = raw_text[number_start:number_end]
            if ordinal_prefix_span is not None and "." in number:
                continue
            boundary_start = (
                ordinal_prefix_span.start
                if ordinal_prefix_span is not None
                else number_start
            )
            if not _valid_left_boundary(raw_text, boundary_start):
                continue
            if not _valid_right_boundary(raw_text, suffix_end):
                if ordinal_prefix_span is None:
                    preserve_end = (
                        _prefixed_ordinal_like_token_end(raw_text, number_start)
                        or suffix_end
                    )
                    preserve_span = SourceSpan(number_start, preserve_end)
                    candidates.append(
                        SurfaceCandidate(
                            core_span=preserve_span,
                            full_span=preserve_span,
                            owner="preserve",
                            surface_type="NUMERIC_SUFFIX_PRESERVE_SURFACE",
                            reason="numeric_suffix_unsafe_tail_preserve",
                        )
                    )
                    break
                continue
            reading = (
                read_sino_time_suffix_number_text(number)
                if ordinal_prefix_span is None and suffix in {"분", "초"}
                else read_number_text(number)
            )
            if reading is None:
                if ordinal_prefix_span is None:
                    preserve_end = (
                        _prefixed_ordinal_like_token_end(raw_text, number_start)
                        or suffix_end
                    )
                    preserve_span = SourceSpan(number_start, preserve_end)
                    candidates.append(
                        SurfaceCandidate(
                            core_span=preserve_span,
                            full_span=preserve_span,
                            owner="preserve",
                            surface_type="NUMERIC_SUFFIX_PRESERVE_SURFACE",
                            reason="numeric_suffix_invalid_number_preserve",
                        )
                    )
                    break
                continue
            if ordinal_prefix_span is not None:
                full_span = SourceSpan(ordinal_prefix_span.start, suffix_end)
                candidates.append(
                    SurfaceCandidate(
                        core_span=full_span,
                        full_span=full_span,
                        owner="numeric_suffix",
                        surface_type="NUMERIC_SUFFIX_SURFACE",
                        suffix_spans=[SourceSpan(suffix_start, suffix_end)],
                        reason="prefixed_ordinal_numeric_suffix",
                        metadata={
                            "number": number,
                            "suffix": suffix,
                            "reading": _prefixed_ordinal_reading(
                                reading,
                                suffix,
                                unit_space=suffix_start > number_end,
                            ),
                        },
                    )
                )
                break
            candidates.append(
                SurfaceCandidate(
                    core_span=SourceSpan(number_start, number_end),
                    full_span=SourceSpan(number_start, suffix_end),
                    owner="numeric_suffix",
                    surface_type="NUMERIC_SUFFIX_SURFACE",
                    suffix_spans=[SourceSpan(suffix_start, suffix_end)],
                    reason="numeric_korean_suffix_fallback",
                    metadata={
                        "number": number,
                        "suffix": suffix,
                        "reading": (
                            f"{reading} "
                            if (
                                suffix in SPACED_UNPREFIXED_NUMERIC_SUFFIXES
                                and suffix_start == number_end
                            )
                            else reading
                        ),
                    },
                )
            )
            break
        if (
            ordinal_prefix_span is not None
            and not _has_candidate_at(candidates, ordinal_prefix_span.start)
        ):
            number = raw_text[number_start:number_end]
            next_char = raw_text[number_end] if number_end < len(raw_text) else None
            code_like_tail = next_char is not None and (
                (next_char.isascii() and next_char.isalnum())
                or next_char in {",", ".", "-", "_", "/"}
            )
            if matched_suffix or "." in number or code_like_tail:
                preserve_end = _prefixed_ordinal_like_token_end(raw_text, number_start)
                if preserve_end is not None:
                    candidates.append(
                        SurfaceCandidate(
                            core_span=SourceSpan(
                                ordinal_prefix_span.start, preserve_end
                            ),
                            full_span=SourceSpan(
                                ordinal_prefix_span.start, preserve_end
                            ),
                            owner="preserve",
                            surface_type="NUMERIC_SUFFIX_PRESERVE_SURFACE",
                            reason=(
                                "prefixed_ordinal_numeric_suffix_invalid"
                                if matched_suffix
                                else "prefixed_ordinal_numeric_suffix_unregistered"
                            ),
                        )
                    )
            else:
                reading = read_number_text(number)
                if reading is not None and _valid_left_boundary(
                    raw_text, ordinal_prefix_span.start
                ):
                    full_span = SourceSpan(ordinal_prefix_span.start, number_end)
                    candidates.append(
                        SurfaceCandidate(
                            core_span=full_span,
                            full_span=full_span,
                            owner="numeric_suffix",
                            surface_type="NUMERIC_SUFFIX_SURFACE",
                            reason="prefixed_ordinal_numeric_core",
                            metadata={
                                "number": number,
                                "reading": f"제 {reading}",
                            },
                        )
                    )
        index = max(number_end, index + 1)
    return candidates


def parse_numeric_suffix_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "numeric_suffix":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    return read_number_text(raw_text[candidate.core_span.start : candidate.core_span.end])


def has_ordinal_je_prefix(raw_text: str, number_start: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(number_start, int):
        raise TypeError("number_start must be int")
    return _ordinal_prefix_span(raw_text, number_start) is not None


def starts_with_longer_registered_numeric_suffix(
    raw_text: str,
    suffix_start: int,
    short_suffix: str,
) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(suffix_start, int):
        raise TypeError("suffix_start must be int")
    if not isinstance(short_suffix, str):
        raise TypeError("short_suffix must be str")
    return any(
        len(suffix) > len(short_suffix)
        and suffix.startswith(short_suffix)
        and raw_text.startswith(suffix, suffix_start)
        for suffix in _ORDERED_SUFFIXES
    )


def _consume_number(raw_text: str, start: int) -> int | None:
    integer_end = _consume_integer(raw_text, start)
    if integer_end is None:
        return None
    if integer_end < len(raw_text) and raw_text[integer_end] == ".":
        fraction_start = integer_end + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return integer_end
        return fraction_end
    return integer_end


def _consume_integer(raw_text: str, start: int) -> int | None:
    digit_end = _consume_digits(raw_text, start)
    if digit_end == start:
        return None
    if digit_end >= len(raw_text) or raw_text[digit_end] != ",":
        return digit_end
    if digit_end - start > 3:
        return None
    index = digit_end
    while index < len(raw_text) and raw_text[index] == ",":
        group_start = index + 1
        group_end = _consume_digits(raw_text, group_start)
        if group_end - group_start != 3:
            return None
        index = group_end
    return index


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _prefixed_ordinal_reading(
    number_reading: str, suffix: str, *, unit_space: bool
) -> str:
    joiner = " " if suffix in SOURCE_SPACED_PREFIXED_SUFFIXES and unit_space else ""
    return f"제 {number_reading}{joiner}{suffix}"


def _suffix_start_for_match(
    raw_text: str,
    number_end: int,
    suffix: str,
    ordinal_prefix_span: SourceSpan | None,
) -> int:
    if ordinal_prefix_span is not None and suffix in SOURCE_SPACED_PREFIXED_SUFFIXES:
        return _consume_optional_ascii_space(raw_text, number_end)
    if suffix in PREFIXED_ONLY_SUFFIXES and ordinal_prefix_span is not None:
        return number_end
    return _consume_optional_ascii_space(raw_text, number_end)


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _ordinal_prefix_span(raw_text: str, number_start: int) -> SourceSpan | None:
    if number_start > 0 and raw_text[number_start - 1] == "제":
        prefix_start = number_start - 1
    elif (
        number_start > 1
        and raw_text[number_start - 1] == " "
        and raw_text[number_start - 2] == "제"
    ):
        prefix_start = number_start - 2
    else:
        return None
    if prefix_start > 0 and not raw_text[prefix_start - 1].isspace():
        return None
    return SourceSpan(prefix_start, number_start)


def _prefixed_ordinal_like_token_end(raw_text: str, number_start: int) -> int | None:
    index = number_start
    while index < len(raw_text) and (
        _is_ascii_digit(raw_text[index]) or raw_text[index] in {",", "."}
    ):
        index += 1
    if index < len(raw_text) and raw_text[index] == "-":
        index += 1
        while index < len(raw_text) and _is_complete_hangul(raw_text[index]):
            index += 1
        return index
    if index < len(raw_text) and (
        _is_complete_hangul(raw_text[index])
        or (raw_text[index].isascii() and raw_text[index].isalpha())
    ):
        index += 1
        while index < len(raw_text) and (
            _is_complete_hangul(raw_text[index])
            or (raw_text[index].isascii() and raw_text[index].isalnum())
        ):
            index += 1
        return index
    return None


def _has_candidate_at(candidates: list[SurfaceCandidate], start: int) -> bool:
    return any(candidate.core_span.start == start for candidate in candidates)


def _valid_left_boundary(raw_text: str, number_start: int) -> bool:
    prev_char = raw_text[number_start - 1] if number_start > 0 else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3" and prev_char != "제":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
    return True


def _valid_right_boundary(raw_text: str, suffix_end: int) -> bool:
    next_char = raw_text[suffix_end] if suffix_end < len(raw_text) else None
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    return True


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_complete_hangul(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


__all__ = [
    "NUMERIC_SUFFIXES",
    "ORDINAL_SUFFIXES",
    "has_ordinal_je_prefix",
    "parse_numeric_suffix_candidate",
    "scan_numeric_suffix_candidates",
    "starts_with_longer_registered_numeric_suffix",
]
