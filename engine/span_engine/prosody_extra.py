from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import RenderPiece, TraceLogEntry
from engine.span_engine.protected import protected_literal_spans

_SENTENCE_BOUNDARIES = frozenset(".!?\n")
_STRONG_PUNCTUATION = frozenset(",:;.!?\n")
_PREDICATE_LIKE_SUFFIXES = (
    "밝혔습니다",
    "발표했습니다",
    "전했습니다",
    "했습니다",
    "열립니다",
    "됩니다",
    "입니다",
    "습니다",
    "합니다",
    "했다",
    "됐다",
    "한다",
    "된다",
    "다",
)
_TIME_FRAME_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(오늘|내일|어제)\s+(아침|오전|오후|저녁)\b"), "time_day_part"),
    (re.compile(r"^(오늘|내일)\s+서울에서\b"), "time_place_frame"),
    (re.compile(r"^(지난달|지난해|올해)\b"), "time_period"),
    (re.compile(r"^(이번\s+주|다음\s+주)\b"), "time_week"),
    (re.compile(r"^지난\s+\d+일\b"), "time_recent_days"),
)
_SUBORDINATE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"고\s+나서\b"), "subordinate_go_naseo"),
    (re.compile(r"[가-힣]*(?:한|난)\s+뒤\b"), "subordinate_han_dwi"),
    (re.compile(r"[가-힣]*(?:한|난)\s+이후\b"), "subordinate_han_ihu"),
    (re.compile(r"[가-힣]*(?:한|난)\s+다음\b"), "subordinate_han_daeum"),
    (re.compile(r"하는\s+경우\b"), "subordinate_haneun_gyeongu"),
    (re.compile(r"[가-힣]+지만\b"), "subordinate_jiman"),
)
_MIN_DISTANCE_BETWEEN_INSERTIONS = 18


@dataclass
class ExtraProsodyCommaResult:
    pieces: list[RenderPiece]
    logs: list[TraceLogEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ExtraProsodyCommaCandidate:
    insert_pos: int
    sentence_id: int
    rule: str
    priority: int
    confidence: float
    reason: str


@dataclass(frozen=True)
class _ExtraProsodySafetyContext:
    blocked_ranges: tuple[tuple[int, int], ...]
    starts: tuple[int, ...]


@dataclass(frozen=True)
class _SentenceCommaContext:
    original_commas: int
    generated_commas: int
    generated_comma_positions: tuple[int, ...]


def apply_extra_prosody_comma_adapter(
    pieces: list[RenderPiece],
    raw_text: str,
    bracket_ranges: list[BracketRange] | None = None,
) -> ExtraProsodyCommaResult:
    if not isinstance(pieces, list):
        raise TypeError("pieces must be list[RenderPiece]")
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if bracket_ranges is None:
        bracket_ranges = []

    safety = _build_safety_context(pieces, raw_text, bracket_ranges)
    sentence_ranges = _sentence_ranges(raw_text)
    generated_comma_positions = _generated_comma_positions(pieces)
    comma_contexts = [
        _sentence_comma_context(raw_text, start, end, generated_comma_positions)
        for start, end in sentence_ranges
    ]
    candidates = _find_candidates(raw_text, sentence_ranges, safety)
    selected = _select_candidates(raw_text, sentence_ranges, comma_contexts, candidates)
    if not selected:
        return ExtraProsodyCommaResult(list(pieces), [])

    updated_pieces = list(pieces)
    logs: list[TraceLogEntry] = []
    for candidate in sorted(selected, key=lambda item: item.insert_pos, reverse=True):
        if _has_existing_punctuation_at(raw_text, candidate.insert_pos):
            continue
        piece_index = _find_piece_index_for_insertion(updated_pieces, candidate.insert_pos)
        if piece_index is None:
            continue
        updated_pieces.insert(piece_index, _make_extra_prosody_comma_piece(candidate))
        logs.append(
            TraceLogEntry(
                stage="prosody",
                event="insert_extra_comma",
                owner="prosody_extra",
                decision="insert",
                reason=candidate.reason,
                action="insert_generated_punct",
                metadata={
                    "prosody_type": "extra_comma",
                    "rule": candidate.rule,
                    "insert_after": candidate.insert_pos,
                    "confidence": candidate.confidence,
                },
            )
        )
    logs.reverse()
    return ExtraProsodyCommaResult(updated_pieces, logs)


def _build_safety_context(
    pieces: list[RenderPiece],
    raw_text: str,
    bracket_ranges: list[BracketRange],
) -> _ExtraProsodySafetyContext:
    ranges: list[tuple[int, int]] = [
        (bracket_range.span.start, bracket_range.span.end)
        for bracket_range in bracket_ranges
    ]
    ranges.extend((span.start, span.end) for span in protected_literal_spans(raw_text))

    for piece in pieces:
        if piece.source_span is None:
            continue
        if piece.owner is not None or piece.provenance == "GENERATED_READING":
            ranges.append((piece.source_span.start, piece.source_span.end))

    merged = tuple(_merge_ranges(ranges))
    return _ExtraProsodySafetyContext(
        blocked_ranges=merged,
        starts=tuple(start for start, _ in merged),
    )


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    normalized = sorted((start, end) for start, end in ranges if start < end)
    if not normalized:
        return []
    merged = [normalized[0]]
    for start, end in normalized[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
            continue
        merged.append((start, end))
    return merged


def _find_candidates(
    raw_text: str,
    sentence_ranges: list[tuple[int, int]],
    safety: _ExtraProsodySafetyContext,
) -> list[ExtraProsodyCommaCandidate]:
    candidates: list[ExtraProsodyCommaCandidate] = []
    for sentence_id, (sentence_start, sentence_end) in enumerate(sentence_ranges):
        sentence = raw_text[sentence_start:sentence_end]
        candidates.extend(
            _leading_time_frame_candidates(
                raw_text, sentence, sentence_id, sentence_start, sentence_end, safety
            )
        )
        candidates.extend(
            _subordinate_marker_candidates(
                raw_text, sentence_id, sentence_start, sentence_end, safety
            )
        )
        candidates.extend(
            _serial_list_candidates(
                raw_text, sentence_id, sentence_start, sentence_end, safety
            )
        )
    return _dedupe_candidates(candidates)


def _leading_time_frame_candidates(
    raw_text: str,
    sentence: str,
    sentence_id: int,
    sentence_start: int,
    sentence_end: int,
    safety: _ExtraProsodySafetyContext,
) -> list[ExtraProsodyCommaCandidate]:
    sentence_offset = len(sentence) - len(sentence.lstrip())
    start = sentence_start + sentence_offset
    if start >= sentence_end or _is_blocked(start, safety):
        return []
    if not _is_sentence_start(raw_text, start):
        return []

    trimmed = raw_text[start:sentence_end]
    for pattern, reason in _TIME_FRAME_PATTERNS:
        match = pattern.match(trimmed)
        if match is None:
            continue
        phrase = match.group(0)
        visible_len = _visible_len(phrase)
        if visible_len < 2 or visible_len > 15:
            return []
        insert_pos = start + match.end()
        if not _candidate_boundary_is_safe(raw_text, insert_pos, sentence_end, safety):
            return []
        right = raw_text[insert_pos:sentence_end].strip(" \t\r\n.,:;!?")
        if reason == "time_period" and _starts_with_basic_topic(right):
            return []
        if not _has_meaningful_clause(right):
            return []
        return [
            ExtraProsodyCommaCandidate(
                insert_pos=insert_pos,
                sentence_id=sentence_id,
                rule="leading_time_frame",
                priority=300,
                confidence=0.94,
                reason=reason,
            )
        ]
    return []


def _subordinate_marker_candidates(
    raw_text: str,
    sentence_id: int,
    sentence_start: int,
    sentence_end: int,
    safety: _ExtraProsodySafetyContext,
) -> list[ExtraProsodyCommaCandidate]:
    candidates: list[ExtraProsodyCommaCandidate] = []
    sentence = raw_text[sentence_start:sentence_end]
    for pattern, reason in _SUBORDINATE_PATTERNS:
        for match in pattern.finditer(sentence):
            marker_start = sentence_start + match.start()
            marker_end = sentence_start + match.end()
            if reason == "subordinate_jiman" and raw_text[marker_start:marker_end] == "하지만":
                continue
            if marker_start <= sentence_start or marker_end >= sentence_end:
                continue
            if _is_blocked(marker_start, safety) or _is_blocked(marker_end - 1, safety):
                continue
            if not raw_text[marker_end].isspace():
                continue
            insert_pos = marker_end
            if not _candidate_boundary_is_safe(raw_text, insert_pos, sentence_end, safety):
                continue
            left = raw_text[sentence_start:insert_pos].strip(" \t\r\n.,:;!?")
            right = raw_text[insert_pos:sentence_end].strip(" \t\r\n.,:;!?")
            if not _has_min_chunks(left, 2) or not _has_min_chunks(right, 2):
                continue
            candidates.append(
                ExtraProsodyCommaCandidate(
                    insert_pos=insert_pos,
                    sentence_id=sentence_id,
                    rule="subordinate_marker",
                    priority=200,
                    confidence=0.91,
                    reason=reason,
                )
            )
            break
    return candidates


def _serial_list_candidates(
    raw_text: str,
    sentence_id: int,
    sentence_start: int,
    sentence_end: int,
    safety: _ExtraProsodySafetyContext,
) -> list[ExtraProsodyCommaCandidate]:
    candidates: list[ExtraProsodyCommaCandidate] = []
    search_start = sentence_start
    while search_start < sentence_end:
        connector_start = raw_text.find("그리고", search_start, sentence_end)
        if connector_start < 0:
            break
        connector_end = connector_start + len("그리고")
        search_start = connector_end
        if connector_start <= sentence_start:
            continue
        if _is_blocked(connector_start, safety) or _is_blocked(connector_end - 1, safety):
            continue
        if not _has_space_boundary(raw_text, connector_start, connector_end, sentence_end):
            continue
        insert_pos = _previous_whitespace_run_start(raw_text, connector_start)
        if not _candidate_boundary_is_safe(raw_text, insert_pos, sentence_end, safety):
            continue
        if not _has_clear_serial_list(raw_text[sentence_start:insert_pos]):
            continue
        right = raw_text[connector_end:sentence_end].strip(" \t\r\n.,:;!?")
        if not _has_min_chunks(right, 2):
            continue
        candidates.append(
            ExtraProsodyCommaCandidate(
                insert_pos=insert_pos,
                sentence_id=sentence_id,
                rule="serial_list",
                priority=100,
                confidence=0.86,
                reason="serial_parallel_3plus",
            )
        )
    return candidates


def _select_candidates(
    raw_text: str,
    sentence_ranges: list[tuple[int, int]],
    comma_contexts: list[_SentenceCommaContext],
    candidates: list[ExtraProsodyCommaCandidate],
) -> list[ExtraProsodyCommaCandidate]:
    selected: list[ExtraProsodyCommaCandidate] = []
    for sentence_id, (sentence_start, sentence_end) in enumerate(sentence_ranges):
        sentence_candidates = [
            candidate for candidate in candidates if candidate.sentence_id == sentence_id
        ]
        if not sentence_candidates:
            continue
        budget = _sentence_budget(
            raw_text[sentence_start:sentence_end], comma_contexts[sentence_id]
        )
        if budget <= 0:
            continue
        chosen: list[ExtraProsodyCommaCandidate] = []
        for candidate in sorted(
            sentence_candidates,
            key=lambda item: (-item.priority, -item.confidence, item.insert_pos),
        ):
            if len(chosen) >= budget:
                break
            existing_positions = [
                other.insert_pos for other in chosen
            ] + _raw_comma_positions(raw_text, sentence_start, sentence_end)
            existing_positions.extend(comma_contexts[sentence_id].generated_comma_positions)
            if any(
                abs(candidate.insert_pos - position) < _MIN_DISTANCE_BETWEEN_INSERTIONS
                for position in existing_positions
            ):
                continue
            chosen.append(candidate)
        selected.extend(chosen)
    return selected


def _sentence_budget(sentence: str, comma_context: _SentenceCommaContext) -> int:
    visible_chars = _visible_len(sentence)
    if visible_chars < 12:
        return 0
    if visible_chars < 90:
        budget = 1
    else:
        budget = 2
    if comma_context.generated_commas > 0:
        budget = max(0, budget - 1)
    if comma_context.original_commas + comma_context.generated_commas >= 1:
        budget = min(budget, 1)
    if comma_context.original_commas >= 2:
        budget = 0
    return budget


def _sentence_ranges(raw_text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    index = 0
    while index < len(raw_text):
        char = raw_text[index]
        if char == "\n":
            ranges.append((start, index + 1))
            start = index + 1
        elif char in ".!?":
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


def _sentence_comma_context(
    raw_text: str,
    start: int,
    end: int,
    generated_comma_positions: list[int],
) -> _SentenceCommaContext:
    sentence_generated_positions = tuple(
        position for position in generated_comma_positions if start <= position < end
    )
    return _SentenceCommaContext(
        original_commas=raw_text.count(",", start, end),
        generated_commas=len(sentence_generated_positions),
        generated_comma_positions=sentence_generated_positions,
    )


def _generated_comma_positions(pieces: list[RenderPiece]) -> list[int]:
    positions: list[int] = []
    previous_source_end = 0
    for index, piece in enumerate(pieces):
        if piece.source_span is not None:
            previous_source_end = piece.source_span.end
            continue
        if (
            piece.text != ","
            or piece.provenance != "GENERATED_PUNCT"
            or piece.owner not in {"prosody", "prosody_extra"}
        ):
            continue
        next_source_start = _next_source_start(pieces, index + 1)
        positions.append(next_source_start if next_source_start is not None else previous_source_end)
    return positions


def _next_source_start(pieces: list[RenderPiece], start: int) -> int | None:
    for piece in pieces[start:]:
        if piece.source_span is not None:
            return piece.source_span.start
    return None


def _candidate_boundary_is_safe(
    raw_text: str,
    insert_pos: int,
    sentence_end: int,
    safety: _ExtraProsodySafetyContext,
) -> bool:
    if not _is_safe_insertion_position(insert_pos, safety):
        return False
    if _has_existing_punctuation_at(raw_text, insert_pos):
        return False
    next_index = _next_non_space_index(raw_text, insert_pos)
    if next_index is None or next_index >= sentence_end:
        return False
    return raw_text[next_index] not in _STRONG_PUNCTUATION


def _has_existing_punctuation_at(raw_text: str, insert_pos: int) -> bool:
    previous_index = _previous_visible_index(raw_text, insert_pos)
    if previous_index is not None and raw_text[previous_index] in _STRONG_PUNCTUATION:
        return True
    next_index = _next_non_space_index(raw_text, insert_pos)
    return next_index is not None and raw_text[next_index] in _STRONG_PUNCTUATION


def _has_meaningful_clause(text: str) -> bool:
    if not _has_min_chunks(text, 2):
        return False
    return _has_predicate_like_content(text)


def _has_min_chunks(text: str, count: int) -> bool:
    return len([chunk for chunk in text.split() if chunk]) >= count


def _has_predicate_like_content(text: str) -> bool:
    stripped = text.strip(" \t\r\n.,:;!?")
    return any(stripped.endswith(suffix) for suffix in _PREDICATE_LIKE_SUFFIXES)


def _starts_with_basic_topic(text: str) -> bool:
    chunks = [chunk for chunk in text.split() if chunk]
    if not chunks:
        return False
    first = chunks[0].strip(" \t\r\n,.;:!?")
    if first in {"우리는", "저희는", "나는", "저는"}:
        return False
    return first.endswith(("은", "는"))


def _has_clear_serial_list(text: str) -> bool:
    stripped = text.strip(" \t\r\n")
    if not stripped:
        return False
    if any(char.isdigit() or char in "/\\@`{}[]:" for char in stripped):
        return False
    if "," in stripped:
        items = [item.strip() for item in stripped.split(",") if item.strip()]
        return len(items) >= 3 and all(_is_short_natural_item(item) for item in items[-3:])

    chunks = [chunk for chunk in stripped.split() if chunk]
    if len(chunks) < 3:
        return False
    items = chunks[-3:]
    if not all(_is_short_natural_item(item) for item in items):
        return False
    return all(item.endswith(("와", "과")) for item in items[:-1])


def _is_short_natural_item(item: str) -> bool:
    compact = item.strip(" \t\r\n,")
    if not compact or _visible_len(compact) > 8:
        return False
    return bool(re.fullmatch(r"[가-힣]+(?:와|과|은|는|이|가|을|를)?", compact))


def _dedupe_candidates(
    candidates: list[ExtraProsodyCommaCandidate],
) -> list[ExtraProsodyCommaCandidate]:
    deduped: list[ExtraProsodyCommaCandidate] = []
    seen: set[tuple[int, int]] = set()
    for candidate in sorted(
        candidates, key=lambda item: (item.sentence_id, item.insert_pos, -item.priority)
    ):
        key = (candidate.sentence_id, candidate.insert_pos)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _is_blocked(index: int, safety: _ExtraProsodySafetyContext) -> bool:
    range_index = bisect_right(safety.starts, index) - 1
    if range_index < 0:
        return False
    start, end = safety.blocked_ranges[range_index]
    return start < index < end


def _is_safe_insertion_position(
    index: int, safety: _ExtraProsodySafetyContext
) -> bool:
    return not _is_blocked(index, safety)


def _is_sentence_start(raw_text: str, start: int) -> bool:
    prefix = raw_text[:start].rstrip()
    return not prefix or prefix[-1] in _SENTENCE_BOUNDARIES


def _has_space_boundary(
    raw_text: str, start: int, end: int, sentence_end: int
) -> bool:
    return (
        start > 0
        and raw_text[start - 1].isspace()
        and end < sentence_end
        and raw_text[end].isspace()
    )


def _previous_whitespace_run_start(raw_text: str, end: int) -> int:
    index = end
    while index > 0 and raw_text[index - 1].isspace():
        index -= 1
    return index


def _previous_visible_index(raw_text: str, start: int) -> int | None:
    index = start - 1
    while index >= 0 and raw_text[index].isspace():
        index -= 1
    return index if index >= 0 else None


def _next_non_space_index(raw_text: str, start: int) -> int | None:
    index = start
    while index < len(raw_text) and raw_text[index].isspace():
        index += 1
    if index >= len(raw_text):
        return None
    return index


def _raw_comma_positions(raw_text: str, start: int, end: int) -> list[int]:
    return [index for index in range(start, end) if raw_text[index] == ","]


def _visible_len(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _find_piece_index_for_insertion(
    pieces: list[RenderPiece], insert_at: int
) -> int | None:
    for index, piece in enumerate(pieces):
        if piece.source_span is None:
            continue
        if piece.source_span.start <= insert_at < piece.source_span.end:
            return index
    return None


def _make_extra_prosody_comma_piece(
    candidate: ExtraProsodyCommaCandidate,
) -> RenderPiece:
    return RenderPiece(
        text=",",
        provenance="GENERATED_PUNCT",
        source_span=None,
        owner="prosody_extra",
        metadata={
            "prosody_type": "extra_comma",
            "rule": candidate.rule,
            "reason": candidate.reason,
        },
    )


__all__ = [
    "ExtraProsodyCommaCandidate",
    "ExtraProsodyCommaResult",
    "apply_extra_prosody_comma_adapter",
]
