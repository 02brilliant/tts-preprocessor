from __future__ import annotations

from engine.span_engine.models import RenderPiece


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    normalized = sorted((start, end) for start, end in ranges if start < end)
    if not normalized:
        return []

    merged = [normalized[0]]
    for start, end in normalized[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
            continue
        merged.append((start, end))
    return merged


def previous_visible_index(raw_text: str, start: int) -> int | None:
    index = start - 1
    while index >= 0 and raw_text[index].isspace():
        index -= 1
    return index if index >= 0 else None


def previous_whitespace_run_start(raw_text: str, end: int) -> int:
    index = end
    while index > 0 and raw_text[index - 1].isspace():
        index -= 1
    return index


def next_non_space_index(raw_text: str, start: int) -> int | None:
    index = start
    while index < len(raw_text) and raw_text[index].isspace():
        index += 1
    if index >= len(raw_text):
        return None
    return index


def find_piece_index_for_insertion(
    pieces: list[RenderPiece], insert_at: int
) -> int | None:
    for index, piece in enumerate(pieces):
        if piece.source_span is None:
            continue
        if piece.source_span.start <= insert_at < piece.source_span.end:
            return index
    return None


__all__ = [
    "find_piece_index_for_insertion",
    "merge_ranges",
    "next_non_space_index",
    "previous_visible_index",
    "previous_whitespace_run_start",
]
