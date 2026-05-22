from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.span_engine.claim_registry import SurfaceClaimRegistry, spans_overlap
from engine.span_engine.models import ClaimedRange, RenderPiece, SourceSpan, TraceLogEntry


@dataclass(frozen=True)
class BracketRange:
    bracket_type: str
    span: SourceSpan
    inner_span: SourceSpan
    raw: str
    complete: bool = True
    outermost: bool = True

    def __post_init__(self) -> None:
        if self.bracket_type not in {"square", "parenthesis"}:
            raise ValueError("bracket_type must be square or parenthesis")
        if not isinstance(self.span, SourceSpan):
            raise TypeError("span must be SourceSpan")
        if not isinstance(self.inner_span, SourceSpan):
            raise TypeError("inner_span must be SourceSpan")
        if not isinstance(self.raw, str):
            raise TypeError("raw must be str")
        if not isinstance(self.complete, bool):
            raise TypeError("complete must be bool")
        if not isinstance(self.outermost, bool):
            raise TypeError("outermost must be bool")


@dataclass
class ProtectedBracketResult:
    protected_ranges: list[BracketRange] = field(default_factory=list)


@dataclass
class BracketFilterResult:
    normalized_text: str
    logs: list[TraceLogEntry] = field(default_factory=list)


class _Marker:
    pass


_PARENTHESIS_MARKER = _Marker()
_OPEN_TO_TYPE = {"[": "square", "(": "parenthesis"}
_CLOSE_TO_OPEN = {"]": "[", ")": "("}


def find_bracket_ranges(raw_text: str) -> list[BracketRange]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    stack: list[tuple[str, int]] = []
    ranges: list[BracketRange] = []
    for index, char in enumerate(raw_text):
        if char in _OPEN_TO_TYPE:
            stack.append((char, index))
            continue
        expected_open = _CLOSE_TO_OPEN.get(char)
        if expected_open is None:
            continue
        if not stack or stack[-1][0] != expected_open:
            continue
        open_char, start = stack.pop()
        if not stack:
            end = index + 1
            ranges.append(
                BracketRange(
                    bracket_type=_OPEN_TO_TYPE[open_char],
                    span=SourceSpan(start, end),
                    inner_span=SourceSpan(start + 1, index),
                    raw=raw_text[start:end],
                )
            )
    return ranges


def find_incomplete_bracket_ranges(raw_text: str) -> list[BracketRange]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    stack: list[tuple[str, int]] = []
    incomplete: list[BracketRange] = []
    matched_open_indexes: set[int] = set()
    for index, char in enumerate(raw_text):
        if char in _OPEN_TO_TYPE:
            stack.append((char, index))
            continue
        expected_open = _CLOSE_TO_OPEN.get(char)
        if expected_open is None:
            continue
        if stack and stack[-1][0] == expected_open:
            _, start = stack.pop()
            matched_open_indexes.add(start)
            continue
        start = _previous_boundary(raw_text, index)
        incomplete.append(
            BracketRange(
                bracket_type=_OPEN_TO_TYPE[expected_open],
                span=SourceSpan(start, index + 1),
                inner_span=SourceSpan(start, index),
                raw=raw_text[start : index + 1],
                complete=False,
            )
        )

    for open_char, start in stack:
        if start in matched_open_indexes:
            continue
        incomplete.append(
            BracketRange(
                bracket_type=_OPEN_TO_TYPE[open_char],
                span=SourceSpan(start, len(raw_text)),
                inner_span=SourceSpan(start + 1, len(raw_text)),
                raw=raw_text[start:],
                complete=False,
            )
        )
    return incomplete


def protect_square_brackets_before_claim(
    registry: SurfaceClaimRegistry, bracket_ranges: list[BracketRange]
) -> ProtectedBracketResult:
    if not isinstance(registry, SurfaceClaimRegistry):
        raise TypeError("registry must be SurfaceClaimRegistry")
    if not isinstance(bracket_ranges, list):
        raise TypeError("bracket_ranges must be list[BracketRange]")

    protected: list[BracketRange] = []
    for bracket_range in bracket_ranges:
        if bracket_range.bracket_type != "square":
            continue
        registry.claim(
            ClaimedRange(
                span=bracket_range.span,
                owner="bracket",
                claim_type="preserve",
                surface_type="PROTECTED_LITERAL_SURFACE",
                reason="square_bracket_protection",
            )
        )
        protected.append(bracket_range)
    return ProtectedBracketResult(protected)


def is_span_inside_protected_bracket(
    span: SourceSpan, protected_ranges: list[BracketRange]
) -> bool:
    if not isinstance(span, SourceSpan):
        raise TypeError("span must be SourceSpan")
    return _overlaps_any(span, protected_ranges)


def is_span_inside_parenthesis(
    span: SourceSpan, parenthesis_ranges: list[BracketRange]
) -> bool:
    if not isinstance(span, SourceSpan):
        raise TypeError("span must be SourceSpan")
    return _overlaps_any(span, parenthesis_ranges)


def apply_final_bracket_filter(
    pieces: list[RenderPiece], bracket_ranges: list[BracketRange]
) -> BracketFilterResult:
    if not isinstance(pieces, list):
        raise TypeError("pieces must be list[RenderPiece]")
    if not isinstance(bracket_ranges, list):
        raise TypeError("bracket_ranges must be list[BracketRange]")
    for piece in pieces:
        if not isinstance(piece, RenderPiece):
            raise TypeError("pieces must contain RenderPiece")

    elements: list[str | _Marker] = []
    emitted_parenthesis_markers: set[tuple[int, int]] = set()
    sorted_ranges = sorted(bracket_ranges, key=lambda value: value.span.start)
    square_ranges = [value for value in sorted_ranges if value.bracket_type == "square"]
    parenthesis_ranges = [
        value for value in sorted_ranges if value.bracket_type == "parenthesis"
    ]

    for piece in pieces:
        if piece.source_span is None or piece.provenance.startswith("GENERATED_"):
            if _span_overlaps_ranges(piece.source_span, parenthesis_ranges):
                _append_parenthesis_marker(
                    elements, piece.source_span, emitted_parenthesis_markers
                )
            else:
                elements.append(piece.text)
            continue

        if len(piece.text) != piece.source_span.length:
            elements.append(piece.text)
            continue

        for offset, char in enumerate(piece.text):
            source_index = piece.source_span.start + offset
            parenthesis_range = _range_containing_index(
                source_index, parenthesis_ranges
            )
            if parenthesis_range is not None:
                marker_key = _range_key(parenthesis_range.span)
                if source_index == parenthesis_range.span.start and marker_key not in emitted_parenthesis_markers:
                    elements.append(_PARENTHESIS_MARKER)
                    emitted_parenthesis_markers.add(marker_key)
                continue
            if _is_square_delimiter_index(source_index, square_ranges):
                continue
            elements.append(char)

    logs = [_bracket_log(bracket_range) for bracket_range in sorted_ranges]
    return BracketFilterResult(_collapse_parenthesis_boundary_spaces(elements), logs)


def _overlaps_any(span: SourceSpan, bracket_ranges: list[BracketRange]) -> bool:
    return any(spans_overlap(span, bracket_range.span) for bracket_range in bracket_ranges)


def _span_overlaps_ranges(
    span: SourceSpan | None, bracket_ranges: list[BracketRange]
) -> bool:
    return span is not None and _overlaps_any(span, bracket_ranges)


def _range_containing_index(
    index: int, bracket_ranges: list[BracketRange]
) -> BracketRange | None:
    for bracket_range in bracket_ranges:
        if bracket_range.span.start <= index < bracket_range.span.end:
            return bracket_range
    return None


def _is_square_delimiter_index(
    index: int, square_ranges: list[BracketRange]
) -> bool:
    for bracket_range in square_ranges:
        if index == bracket_range.span.start or index == bracket_range.span.end - 1:
            return True
    return False


def _append_parenthesis_marker(
    elements: list[str | _Marker],
    span: SourceSpan | None,
    emitted_parenthesis_markers: set[tuple[int, int]],
) -> None:
    key = (span.start, span.end) if span is not None else (-1, -1)
    if key not in emitted_parenthesis_markers:
        elements.append(_PARENTHESIS_MARKER)
        emitted_parenthesis_markers.add(key)


def _collapse_parenthesis_boundary_spaces(elements: list[str | _Marker]) -> str:
    if all(element is not _PARENTHESIS_MARKER for element in elements):
        return "".join(str(element) for element in elements)

    result: list[str] = []
    index = 0
    while index < len(elements):
        element = elements[index]
        if element is not _PARENTHESIS_MARKER:
            result.append(str(element))
            index += 1
            continue

        removed_left_space = _remove_trailing_spaces(result)
        index += 1
        removed_right_space = False
        while index < len(elements) and isinstance(elements[index], str) and str(elements[index]).isspace():
            removed_right_space = True
            index += 1

        has_future_text = _has_future_non_space(elements, index)
        if (removed_left_space or removed_right_space) and result and has_future_text:
            result.append(" ")

    return "".join(result).strip()


def _remove_trailing_spaces(values: list[str]) -> bool:
    removed = False
    while values and values[-1].isspace():
        values.pop()
        removed = True
    return removed


def _has_future_non_space(elements: list[str | _Marker], start: int) -> bool:
    return any(
        isinstance(element, str) and not element.isspace()
        for element in elements[start:]
    )


def _bracket_log(bracket_range: BracketRange) -> TraceLogEntry:
    if bracket_range.bracket_type == "square":
        event = "square_bracket_unwrapped"
        action = "unwrap_square_brackets"
    else:
        event = "parenthesis_elided"
        action = "delete_parenthesis_content"
    return TraceLogEntry(
        stage="bracket_filter",
        event=event,
        span=bracket_range.span,
        raw=bracket_range.raw,
        decision="applied",
        reason="final_bracket_filter",
        action=action,
        metadata={
            "bracket_type": bracket_range.bracket_type,
            "inner_span": bracket_range.inner_span,
            "outermost": bracket_range.outermost,
        },
    )


def _range_key(span: SourceSpan) -> tuple[int, int]:
    return (span.start, span.end)


def _previous_boundary(raw_text: str, index: int) -> int:
    cursor = index
    while cursor > 0 and not raw_text[cursor - 1].isspace():
        cursor -= 1
    return cursor


__all__ = [
    "BracketFilterResult",
    "BracketRange",
    "ProtectedBracketResult",
    "apply_final_bracket_filter",
    "find_bracket_ranges",
    "find_incomplete_bracket_ranges",
    "is_span_inside_parenthesis",
    "is_span_inside_protected_bracket",
    "protect_square_brackets_before_claim",
]
