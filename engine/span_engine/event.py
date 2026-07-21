from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate, TraceLogEntry
from engine.span_engine.number import SINO_DIGITS, number_to_korean_under_10000

EVENT_KEYWORDS = (
    "민주화 운동",
    "민주화운동",
    "민주화",
    "비상계엄",
    "기념일",
    "계엄",
    "사태",
    "혁명",
    "전쟁",
    "항쟁",
    "운동",
    "사건",
    "정책",
    "부동산대책",
    "대책",
    "사고",
    "선거",
)
STRONG_EVENT_KEYWORDS = frozenset(
    {
        "민주화 운동",
        "민주화운동",
        "민주화",
        "비상계엄",
        "기념일",
        "계엄",
        "사태",
        "혁명",
        "전쟁",
        "항쟁",
    }
)
KNOWN_EVENT_KEYWORDS = frozenset({"부동산대책"})
WEAK_EVENT_KEYWORDS = frozenset({"운동", "사건", "정책", "대책", "사고", "선거"})
KNOWN_WEAK_EVENT_PATTERNS = frozenset(
    {
        ("3", "1", "운동"),
        ("10", "26", "사건"),
    }
)
WEAK_EVENT_ANCHORS = (
    "사건",
    "역사",
    "정책",
    "발표",
    "대책",
    "부동산",
    "선거",
    "참사",
    "기념",
    "항쟁",
)

_EVENT_RE = re.compile(r"(?<![A-Za-z0-9])(\d{1,2})([.·])(\d{1,2})(?![A-Za-z0-9.·])")


def scan_event_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    for match in _EVENT_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        gate = evaluate_event_gate(raw_text, span, match.group(1), match.group(2), match.group(3))
        if gate["decision"] != "pass":
            if gate.get("reason") == "one_digit_right_block":
                candidates.append(
                    SurfaceCandidate(
                        core_span=span,
                        full_span=span,
                        owner="preserve",
                        surface_type="PRESERVE_SURFACE",
                        reason=gate["reason"],
                    )
                )
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=SourceSpan(span.start, int(gate["keyword_end"])),
                owner="event",
                surface_type="EVENT_SURFACE",
                reason=gate["reason"],
                metadata={
                    "left": match.group(1),
                    "right": match.group(3),
                    "separator": match.group(2),
                    "keyword": gate["keyword"],
                    "keyword_span": SourceSpan(int(gate["keyword_start"]), int(gate["keyword_end"])),
                    "reading": event_number_reading(match.group(1), match.group(3), match.group(2)),
                },
            )
        )
    return candidates


def evaluate_event_gate(
    raw_text: str, span: SourceSpan, left: str, separator: str, right: str
) -> dict[str, str | int]:
    if _has_leading_zero(left) or _has_leading_zero(right):
        return {"decision": "fail", "reason": "leading_zero_event_preserve"}
    if not _is_supported_event_date(left, right):
        return {"decision": "fail", "reason": "event_date_range_fail"}
    keyword = _immediate_event_keyword(raw_text, span.end)
    if keyword is None:
        return {"decision": "fail", "reason": "missing_event_keyword"}
    if not _event_keyword_gate_allows(raw_text, span, left, right, keyword):
        return {"decision": "fail", "reason": "weak_event_keyword_context_fail"}
    
    return {
        "decision": "pass",
        "reason": "event_keyword_gate",
        "keyword": keyword[0],
        "keyword_start": keyword[1],
        "keyword_end": keyword[2],
    }


def parse_event_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "event":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def event_number_reading(left: str, right: str, separator: str = ".") -> str:
    if not isinstance(left, str) or not isinstance(right, str):
        raise TypeError("left and right must be str")
    left_reading = number_to_korean_under_10000(int(left))
    if left == right:
        right_reading = number_to_korean_under_10000(int(right))
    else:
        right_reading = "".join(SINO_DIGITS[int(digit)] for digit in right)
    
    return f"{left_reading}{right_reading}"


def is_one_digit_right_block(left: str, separator: str, right: str) -> bool:
    return separator == "." and len(left) > 1 and len(right) == 1


def build_event_gate_logs(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[TraceLogEntry]:
    if excluded_ranges is None:
        excluded_ranges = []
    logs: list[TraceLogEntry] = []
    for match in _EVENT_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        gate = evaluate_event_gate(
            raw_text, span, match.group(1), match.group(2), match.group(3)
        )
        logs.append(
            TraceLogEntry(
                stage="event_gate",
                event="event_keyword_gate",
                span=span,
                raw=raw_text[span.start : span.end],
                owner="event",
                decision=str(gate["decision"]),
                reason=str(gate["reason"]),
                action="allow_event_parse" if gate["decision"] == "pass" else "preserve",
                metadata={
                    "keyword": gate.get("keyword"),
                    "separator": match.group(2),
                },
            )
        )
    return logs


def _immediate_event_keyword(raw_text: str, end: int) -> tuple[str, int, int] | None:
    for gap in (" ", ""):
        keyword_start = end + len(gap)
        if gap and not raw_text.startswith(gap, end):
            continue
        for keyword in EVENT_KEYWORDS:
            if raw_text.startswith(keyword, keyword_start):
                return (keyword, keyword_start, keyword_start + len(keyword))
    return None


def _event_keyword_gate_allows(
    raw_text: str,
    span: SourceSpan,
    left: str,
    right: str,
    keyword: tuple[str, int, int],
) -> bool:
    keyword_text, _, keyword_end = keyword
    if keyword_text in STRONG_EVENT_KEYWORDS or keyword_text in KNOWN_EVENT_KEYWORDS:
        return True
    if keyword_text not in WEAK_EVENT_KEYWORDS:
        return True
    if (left, right, keyword_text) in KNOWN_WEAK_EVENT_PATTERNS:
        return True
    context_start = max(0, span.start - 12)
    context_end = min(len(raw_text), keyword_end + 12)
    left_context = raw_text[context_start : span.start]
    right_context = raw_text[keyword_end:context_end]
    return any(
        anchor in left_context or anchor in right_context
        for anchor in WEAK_EVENT_ANCHORS
    )


def _is_supported_event_date(left: str, right: str) -> bool:
    left_value = int(left)
    right_value = int(right)
    return 1 <= left_value <= 12 and 1 <= right_value <= 31


def _has_leading_zero(raw: str) -> bool:
    return len(raw) > 1 and raw.startswith("0")


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "EVENT_KEYWORDS",
    "build_event_gate_logs",
    "evaluate_event_gate",
    "event_number_reading",
    "is_one_digit_right_block",
    "parse_event_candidate",
    "scan_event_candidates",
]
