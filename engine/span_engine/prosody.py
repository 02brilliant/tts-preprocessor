from __future__ import annotations

from dataclasses import dataclass, field

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import RenderPiece, TraceLogEntry

LEADING_CONNECTORS = ("그리고", "그러나", "하지만", "그런데", "따라서")
_SENTENCE_BOUNDARIES = frozenset(".!?")
_BLOCKING_AFTER_CONNECTOR = frozenset(",:;.!?")


@dataclass
class ProsodyCommaResult:
    pieces: list[RenderPiece]
    logs: list[TraceLogEntry] = field(default_factory=list)


def apply_prosody_comma_adapter(
    pieces: list[RenderPiece],
    raw_text: str,
    bracket_ranges: list[BracketRange] | None = None,
) -> ProsodyCommaResult:
    if not isinstance(pieces, list):
        raise TypeError("pieces must be list[RenderPiece]")
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if bracket_ranges is None:
        bracket_ranges = []

    insertion_specs: list[tuple[int, str]] = []
    search_start = 0
    while search_start < len(raw_text):
        match = _find_next_connector(raw_text, search_start)
        if match is None:
            break
        connector_start, connector = match
        connector_end = connector_start + len(connector)
        search_start = connector_end
        if _is_inside_bracket(connector_start, bracket_ranges):
            continue
        if not _is_sentence_start_or_after_boundary(raw_text, connector_start):
            continue
        if connector_end >= len(raw_text) or not raw_text[connector_end].isspace():
            continue
        next_non_space_index = _next_non_space_index(raw_text, connector_end)
        if next_non_space_index is None:
            continue
        if raw_text[next_non_space_index] in _BLOCKING_AFTER_CONNECTOR:
            continue
        if _sentence_has_url_path_or_code_like_context(raw_text, connector_start):
            continue
        insertion_specs.append((connector_end, connector))

    if not insertion_specs:
        return ProsodyCommaResult(list(pieces), [])

    updated_pieces = list(pieces)
    logs: list[TraceLogEntry] = []
    for insert_at, connector in sorted(insertion_specs, key=lambda item: item[0], reverse=True):
        piece_index = _find_piece_index_for_insertion(updated_pieces, insert_at)
        if piece_index is None:
            continue
        comma_piece = make_prosody_comma_piece()
        updated_pieces.insert(piece_index, comma_piece)
        logs.append(
            TraceLogEntry(
                stage="prosody",
                event="insert_comma",
                owner="prosody",
                decision="insert",
                reason="leading_connector",
                action="insert_generated_punct",
                metadata={
                    "prosody_type": "comma",
                    "connector": connector,
                    "insert_after": insert_at,
                },
            )
        )
    logs.reverse()
    return ProsodyCommaResult(updated_pieces, logs)


def should_insert_leading_connector_comma(
    raw_text: str, connector_start: int, connector: str, bracket_ranges: list[BracketRange]
) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(connector_start, int):
        raise TypeError("connector_start must be int")
    if not isinstance(connector, str):
        raise TypeError("connector must be str")
    if not isinstance(bracket_ranges, list):
        raise TypeError("bracket_ranges must be list[BracketRange]")

    connector_end = connector_start + len(connector)
    if _is_inside_bracket(connector_start, bracket_ranges):
        return False
    if not _is_sentence_start_or_after_boundary(raw_text, connector_start):
        return False
    if connector_end >= len(raw_text) or not raw_text[connector_end].isspace():
        return False
    next_non_space_index = _next_non_space_index(raw_text, connector_end)
    if next_non_space_index is None:
        return False
    if raw_text[next_non_space_index] in _BLOCKING_AFTER_CONNECTOR:
        return False
    return not _sentence_has_url_path_or_code_like_context(raw_text, connector_start)


def has_url_path_or_code_like_context(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if "http://" in text or "https://" in text:
        return True
    if "_" in text:
        return True
    return text.count("/") >= 2


def make_prosody_comma_piece() -> RenderPiece:
    return RenderPiece(
        text=",",
        provenance="GENERATED_PUNCT",
        source_span=None,
        owner="prosody",
        metadata={"prosody_type": "comma"},
    )


def _find_next_connector(raw_text: str, start: int) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for connector in LEADING_CONNECTORS:
        index = raw_text.find(connector, start)
        if index < 0:
            continue
        if best is None or index < best[0] or (index == best[0] and len(connector) > len(best[1])):
            best = (index, connector)
    return best


def _is_inside_bracket(index: int, bracket_ranges: list[BracketRange]) -> bool:
    return any(bracket_range.span.start < index < bracket_range.span.end - 1 for bracket_range in bracket_ranges)


def _is_sentence_start_or_after_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    prefix = raw_text[:start].rstrip()
    if not prefix:
        return True
    return prefix[-1] in _SENTENCE_BOUNDARIES


def _next_non_space_index(raw_text: str, start: int) -> int | None:
    index = start
    while index < len(raw_text) and raw_text[index].isspace():
        index += 1
    if index >= len(raw_text):
        return None
    return index


def _sentence_has_url_path_or_code_like_context(raw_text: str, connector_start: int) -> bool:
    sentence_end = connector_start
    while sentence_end < len(raw_text) and raw_text[sentence_end] not in _SENTENCE_BOUNDARIES:
        sentence_end += 1
    return has_url_path_or_code_like_context(raw_text[connector_start:sentence_end])


def _find_piece_index_for_insertion(
    pieces: list[RenderPiece], insert_at: int
) -> int | None:
    for index, piece in enumerate(pieces):
        if piece.source_span is None:
            continue
        if piece.source_span.start <= insert_at < piece.source_span.end:
            return index
    return None


__all__ = [
    "LEADING_CONNECTORS",
    "ProsodyCommaResult",
    "apply_prosody_comma_adapter",
    "has_url_path_or_code_like_context",
    "make_prosody_comma_piece",
    "should_insert_leading_connector_comma",
]
