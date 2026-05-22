from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate, TraceLogEntry
from engine.span_engine.number import SINO_DIGITS

EMERGENCY_READINGS = {
    "112": "일일이",
    "119": "일일구",
}

EMERGENCY_CONTEXT_KEYWORDS = (
    "긴급번호",
    "긴급",
    "신고",
    "응급",
    "구조",
    "출동",
    "경찰",
    "소방",
    "화재",
    "구급",
    "재난",
    "범죄",
)

ALLOWED_EMERGENCY_TAILS = (
    "에서",
    "에게",
    "으로",
    "부터",
    "까지",
    "처럼",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "로",
    "와",
    "과",
    "도",
    "만",
    "",
)

DISALLOWED_EMERGENCY_SUFFIXES = ("명", "건", "번", "호")
_EMERGENCY_RE = re.compile(r"(?<![A-Za-z0-9])(?:112|119)(?![A-Za-z0-9])")


def scan_emergency_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []
    candidates: list[SurfaceCandidate] = []
    sanitized = _mask_ranges(raw_text, excluded_ranges)
    for match in _EMERGENCY_RE.finditer(sanitized):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if span.end < len(raw_text) and raw_text[span.end] in "([":
            continue
        gate = evaluate_emergency_gate(sanitized, span, raw_text[span.start : span.end])
        if gate["decision"] != "pass":
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=SourceSpan(span.start, int(gate["tail_end"])),
                owner="emergency",
                surface_type="EMERGENCY_SURFACE",
                reason=gate["reason"],
                metadata={
                    "tail": gate["tail"],
                    "reading": EMERGENCY_READINGS[match.group(0)],
                    "gate_reason": gate["reason"],
                },
            )
        )
    return candidates


def evaluate_emergency_gate(
    raw_text: str, span: SourceSpan, number: str
) -> dict[str, str | int]:
    if number not in EMERGENCY_READINGS:
        return {"decision": "fail", "reason": "unsupported_emergency_number"}
    tail_info = _allowed_tail_at(raw_text, span.end)
    if tail_info is None:
        return {"decision": "fail", "reason": "disallowed_tail"}
    tail, tail_end = tail_info
    if not has_emergency_context(raw_text, span):
        return {
            "decision": "fail",
            "reason": "missing_context",
            "tail": tail,
            "tail_end": tail_end,
        }
    return {
        "decision": "pass",
        "reason": "emergency_context_tail_gate",
        "tail": tail,
        "tail_end": tail_end,
    }


def parse_emergency_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "emergency":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def has_emergency_context(raw_text: str, span: SourceSpan) -> bool:
    prev_text = raw_text[max(0, span.start - 16) : span.start]
    next_text = raw_text[span.end : min(len(raw_text), span.end + 16)]
    return any(keyword in prev_text or keyword in next_text for keyword in EMERGENCY_CONTEXT_KEYWORDS)


def is_allowed_emergency_tail(tail: str) -> bool:
    return tail in ALLOWED_EMERGENCY_TAILS


def emergency_digit_reading(number: str) -> str | None:
    if number in EMERGENCY_READINGS:
        return EMERGENCY_READINGS[number]
    if not number.isdigit():
        return None
    return "".join(SINO_DIGITS[int(digit)] for digit in number)


def build_emergency_gate_logs(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[TraceLogEntry]:
    if excluded_ranges is None:
        excluded_ranges = []
    sanitized = _mask_ranges(raw_text, excluded_ranges)
    logs: list[TraceLogEntry] = []
    for match in _EMERGENCY_RE.finditer(sanitized):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        raw = raw_text[span.start : span.end]
        if span.end < len(raw_text) and raw_text[span.end] in "([":
            gate = {"decision": "fail", "reason": "context_boundary_block"}
        else:
            gate = evaluate_emergency_gate(sanitized, span, raw)
        logs.append(
            TraceLogEntry(
                stage="emergency_gate",
                event="emergency_context_tail_gate",
                span=span,
                raw=raw,
                owner="emergency",
                decision=str(gate["decision"]),
                reason=str(gate["reason"]),
                action="allow_emergency_parse" if gate["decision"] == "pass" else "number_fallback",
                metadata={"tail": gate.get("tail")},
            )
        )
    return logs


def _allowed_tail_at(raw_text: str, start: int) -> tuple[str, int] | None:
    if start < len(raw_text) and raw_text[start] in "([":
        return None
    remainder = raw_text[start:]
    for suffix in DISALLOWED_EMERGENCY_SUFFIXES:
        if remainder.startswith(suffix):
            return None
    if remainder and remainder[0].isascii() and remainder[0].isalpha():
        return None
    for tail in ALLOWED_EMERGENCY_TAILS:
        if tail and remainder.startswith(tail):
            return tail, start + len(tail)
    if remainder and "\uac00" <= remainder[0] <= "\ud7a3":
        return None
    return "", start


def _mask_ranges(raw_text: str, ranges: list[BracketRange]) -> str:
    chars = list(raw_text)
    for bracket_range in ranges:
        for index in range(bracket_range.span.start, bracket_range.span.end):
            chars[index] = " "
    return "".join(chars)


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "ALLOWED_EMERGENCY_TAILS",
    "DISALLOWED_EMERGENCY_SUFFIXES",
    "EMERGENCY_CONTEXT_KEYWORDS",
    "EMERGENCY_READINGS",
    "build_emergency_gate_logs",
    "emergency_digit_reading",
    "evaluate_emergency_gate",
    "has_emergency_context",
    "is_allowed_emergency_tail",
    "parse_emergency_candidate",
    "scan_emergency_candidates",
]
