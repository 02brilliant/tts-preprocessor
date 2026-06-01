from __future__ import annotations

import re
from collections.abc import Sequence

from engine.span_engine.models import SourceSpan

_FINAL_SLASH_RUN_RE = re.compile(r"/+")


def sentence_final_slash_spans(
    text: str, protected_ranges: Sequence[tuple[int, int]] | None = None
) -> list[SourceSpan]:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if protected_ranges is None:
        protected_ranges = ()

    spans: list[SourceSpan] = []
    for match in _FINAL_SLASH_RUN_RE.finditer(text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_ranges(span.start, span.end, protected_ranges):
            continue
        if not is_sentence_final_slash_boundary(
            text, span.start, protected_ranges=protected_ranges
        ):
            continue
        spans.append(span)
    return spans


def is_sentence_final_slash_boundary(
    text: str,
    slash_start: int,
    protected_ranges: Sequence[tuple[int, int]] | None = None,
) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not isinstance(slash_start, int):
        raise TypeError("slash_start must be int")
    if slash_start < 0 or slash_start >= len(text) or text[slash_start] != "/":
        return False
    if protected_ranges is None:
        protected_ranges = ()

    slash_end = slash_start
    while slash_end < len(text) and text[slash_end] == "/":
        slash_end += 1
    if _span_overlaps_ranges(slash_start, slash_end, protected_ranges):
        return False

    cursor = slash_end
    while cursor < len(text) and text[cursor] in {" ", "\t"}:
        cursor += 1
    if cursor < len(text) and text[cursor] not in {"\r", "\n"}:
        return False
    if cursor < len(text) and text[cursor] == "\r":
        if cursor + 1 < len(text) and text[cursor + 1] != "\n":
            return False

    line_start = text.rfind("\n", 0, slash_start) + 1
    return _has_unprotected_hangul(text, line_start, slash_start, protected_ranges)


def _has_unprotected_hangul(
    text: str,
    start: int,
    end: int,
    protected_ranges: Sequence[tuple[int, int]],
) -> bool:
    for index in range(start, end):
        if not ("\uac00" <= text[index] <= "\ud7a3"):
            continue
        if _span_overlaps_ranges(index, index + 1, protected_ranges):
            continue
        return True
    return False


def _span_overlaps_ranges(
    start: int, end: int, ranges: Sequence[tuple[int, int]]
) -> bool:
    return any(
        start < range_end and range_start < end
        for range_start, range_end in ranges
    )


__all__ = ["is_sentence_final_slash_boundary", "sentence_final_slash_spans"]
