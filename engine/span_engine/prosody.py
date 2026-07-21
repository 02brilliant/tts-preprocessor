from __future__ import annotations

from dataclasses import dataclass, field

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import RenderPiece, TraceLogEntry
from engine.span_engine.protected import protected_literal_spans
from engine.span_engine.prosody_support import (
    find_piece_index_for_insertion as _find_piece_index_for_insertion,
    merge_ranges as _merge_ranges,
    next_non_space_index as _next_non_space_index,
    previous_visible_index as _previous_visible_index,
    previous_whitespace_run_start as _previous_whitespace_run_start,
)

LEADING_CONNECTORS = ("그리고", "그러나", "하지만", "그런데", "따라서")
MID_SENTENCE_DISCOURSE_MARKERS = (
    "이에 따라",
    "그 결과",
    "하지만",
    "그러나",
    "다만",
    "반면",
    "한편",
)
_SENTENCE_BOUNDARIES = frozenset(".!?")
_STRONG_PUNCTUATION = frozenset(",:;.!?\n")
_BLOCKING_AFTER_CONNECTOR = _STRONG_PUNCTUATION - frozenset("\n")
_PREDICATE_LIKE_SUFFIXES = (
    "밝혔습니다",
    "전했습니다",
    "했습니다",
    "됩니다",
    "입니다",
    "습니다",
    "니다",
    "했다",
    "됐다",
    "요",
    "다",
)


@dataclass
class ProsodyCommaResult:
    pieces: list[RenderPiece]
    logs: list[TraceLogEntry] = field(default_factory=list)


@dataclass(frozen=True)
class _InsertionSpec:
    insert_at: int
    marker: str
    reason: str


@dataclass(frozen=True)
class _ProsodySafetyContext:
    protected_ranges: tuple[tuple[int, int], ...]
    owner_surface_ranges: tuple[tuple[int, int], ...]


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

    safety = _build_safety_context(pieces, raw_text, bracket_ranges)
    insertion_specs: list[_InsertionSpec] = []
    search_start = 0
    while search_start < len(raw_text):
        match = _find_next_connector(raw_text, search_start)
        if match is None:
            break
        connector_start, connector = match
        connector_end = connector_start + len(connector)
        search_start = connector_end
        if _is_in_blocked_range(connector_start, safety):
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
        if not _is_safe_insertion_position(connector_end, safety):
            continue
        insertion_specs.append(
            _InsertionSpec(
                insert_at=connector_end,
                marker=connector,
                reason="leading_connector",
            )
        )

    insertion_specs.extend(
        _find_mid_sentence_discourse_marker_specs(raw_text, safety)
    )

    if not insertion_specs:
        return ProsodyCommaResult(list(pieces), [])

    updated_pieces = list(pieces)
    logs: list[TraceLogEntry] = []
    for spec in sorted(
        _dedupe_insertion_specs(insertion_specs), key=lambda item: item.insert_at, reverse=True
    ):
        piece_index = _find_piece_index_for_insertion(updated_pieces, spec.insert_at)
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
                reason=spec.reason,
                action="insert_generated_punct",
                metadata={
                    "prosody_type": "comma",
                    "connector": spec.marker,
                    "insert_after": spec.insert_at,
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


def _build_safety_context(
    pieces: list[RenderPiece],
    raw_text: str,
    bracket_ranges: list[BracketRange],
) -> _ProsodySafetyContext:
    protected_ranges: list[tuple[int, int]] = [
        (bracket_range.span.start, bracket_range.span.end)
        for bracket_range in bracket_ranges
    ]
    protected_ranges.extend(
        (span.start, span.end) for span in protected_literal_spans(raw_text)
    )

    owner_surface_ranges: list[tuple[int, int]] = []
    for piece in pieces:
        if piece.source_span is None:
            continue
        if piece.owner is not None or piece.provenance == "GENERATED_READING":
            owner_surface_ranges.append(
                (piece.source_span.start, piece.source_span.end)
            )

    return _ProsodySafetyContext(
        protected_ranges=tuple(_merge_ranges(protected_ranges)),
        owner_surface_ranges=tuple(_merge_ranges(owner_surface_ranges)),
    )


def _dedupe_insertion_specs(specs: list[_InsertionSpec]) -> list[_InsertionSpec]:
    deduped: list[_InsertionSpec] = []
    seen: set[int] = set()
    for spec in sorted(specs, key=lambda item: item.insert_at):
        if spec.insert_at in seen:
            continue
        seen.add(spec.insert_at)
        deduped.append(spec)
    return deduped


def _is_in_blocked_range(index: int, safety: _ProsodySafetyContext) -> bool:
    return _index_inside_ranges(index, safety.protected_ranges) or _index_inside_ranges(
        index, safety.owner_surface_ranges
    )


def _is_safe_insertion_position(
    index: int, safety: _ProsodySafetyContext
) -> bool:
    return not _is_in_blocked_range(index, safety)


def _index_inside_ranges(index: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start < index < end for start, end in ranges)


def _find_mid_sentence_discourse_marker_specs(
    raw_text: str,
    safety: _ProsodySafetyContext,
) -> list[_InsertionSpec]:
    specs: list[_InsertionSpec] = []
    for sentence_start, sentence_end in _sentence_ranges(raw_text):
        sentence_specs = _find_mid_sentence_specs_in_sentence(
            raw_text, sentence_start, sentence_end, safety
        )
        if sentence_specs:
            specs.append(sentence_specs[0])
    return specs


def _find_mid_sentence_specs_in_sentence(
    raw_text: str,
    sentence_start: int,
    sentence_end: int,
    safety: _ProsodySafetyContext,
) -> list[_InsertionSpec]:
    specs: list[_InsertionSpec] = []
    search_start = sentence_start
    while search_start < sentence_end:
        match = _find_next_mid_sentence_marker(raw_text, search_start, sentence_end)
        if match is None:
            break
        marker_start, marker = match
        marker_end = marker_start + len(marker)
        search_start = marker_end

        if not _should_insert_mid_sentence_discourse_comma(
            raw_text,
            sentence_start,
            sentence_end,
            marker_start,
            marker_end,
            safety,
        ):
            continue
        specs.append(
            _InsertionSpec(
                insert_at=_previous_whitespace_run_start(raw_text, marker_start),
                marker=marker,
                reason="mid_sentence_discourse_marker",
            )
        )
        break
    return specs


def _find_next_mid_sentence_marker(
    raw_text: str, start: int, end: int
) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for marker in MID_SENTENCE_DISCOURSE_MARKERS:
        index = raw_text.find(marker, start, end)
        if index < 0:
            continue
        if best is None or index < best[0] or (
            index == best[0] and len(marker) > len(best[1])
        ):
            best = (index, marker)
    return best


def _should_insert_mid_sentence_discourse_comma(
    raw_text: str,
    sentence_start: int,
    sentence_end: int,
    marker_start: int,
    marker_end: int,
    safety: _ProsodySafetyContext,
) -> bool:
    if marker_start <= sentence_start:
        return False
    if _is_in_blocked_range(marker_start, safety) or _is_in_blocked_range(
        marker_end - 1, safety
    ):
        return False
    if not _is_marker_at_space_boundary(raw_text, marker_start, marker_end, sentence_end):
        return False

    previous_visible = _previous_visible_index(raw_text, marker_start)
    if previous_visible is None or previous_visible < sentence_start:
        return False
    if raw_text[previous_visible] in _STRONG_PUNCTUATION:
        return False

    insert_at = _previous_whitespace_run_start(raw_text, marker_start)
    if not _is_safe_insertion_position(insert_at, safety):
        return False
    left_clause = raw_text[sentence_start : insert_at].strip()
    if not _left_clause_is_sufficient(left_clause):
        return False
    if not _has_predicate_like_ending(left_clause):
        return False
    return _right_side_has_meaningful_content(raw_text, marker_end, sentence_end)


def _sentence_ranges(raw_text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    index = 0
    while index < len(raw_text):
        char = raw_text[index]
        if char == "\n":
            ranges.append((start, index + 1))
            start = index + 1
        elif char in _SENTENCE_BOUNDARIES:
            prev_char = raw_text[index - 1] if index > 0 else ""
            next_char = raw_text[index + 1] if index + 1 < len(raw_text) else ""
            if prev_char.isdigit() and next_char.isdigit():
                index += 1
                continue
            if prev_char.isalpha() and next_char.isalpha():
                index += 1
                continue
            ranges.append((start, index + 1))
            start = index + 1
        index += 1
    if start < len(raw_text):
        ranges.append((start, len(raw_text)))
    return ranges


def _is_marker_at_space_boundary(
    raw_text: str, marker_start: int, marker_end: int, sentence_end: int
) -> bool:
    return (
        marker_start > 0
        and raw_text[marker_start - 1].isspace()
        and marker_end < sentence_end
        and raw_text[marker_end].isspace()
    )


def _left_clause_is_sufficient(left_clause: str) -> bool:
    visible = "".join(char for char in left_clause if not char.isspace())
    if len(visible) < 8:
        return False
    return len([chunk for chunk in left_clause.split() if chunk]) >= 2


def _has_predicate_like_ending(left_clause: str) -> bool:
    trimmed = left_clause.rstrip()
    return any(trimmed.endswith(suffix) for suffix in _PREDICATE_LIKE_SUFFIXES)


def _right_side_has_meaningful_content(
    raw_text: str, marker_end: int, sentence_end: int
) -> bool:
    right = raw_text[marker_end:sentence_end].strip(" \t\r\n.,:;!?")
    return bool(right)


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


def _sentence_has_url_path_or_code_like_context(raw_text: str, connector_start: int) -> bool:
    sentence_end = connector_start
    while sentence_end < len(raw_text) and raw_text[sentence_end] not in _SENTENCE_BOUNDARIES:
        sentence_end += 1
    return has_url_path_or_code_like_context(raw_text[connector_start:sentence_end])


__all__ = [
    "LEADING_CONNECTORS",
    "MID_SENTENCE_DISCOURSE_MARKERS",
    "ProsodyCommaResult",
    "apply_prosody_comma_adapter",
    "has_url_path_or_code_like_context",
    "make_prosody_comma_piece",
    "should_insert_leading_connector_comma",
]
