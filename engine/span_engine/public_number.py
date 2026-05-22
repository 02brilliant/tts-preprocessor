from __future__ import annotations

import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.emergency import ALLOWED_EMERGENCY_TAILS
from engine.span_engine.models import SourceSpan, SurfaceCandidate, TraceLogEntry
from engine.span_engine.number import SINO_DIGITS

PUBLIC_NUMBER_CONTEXTS = {
    "110": ("국민콜", "정부민원", "민원", "상담"),
    "120": ("다산콜", "시정", "지자체", "콜센터", "상담"),
    "117": ("학교폭력", "신고", "상담"),
    "118": ("사이버", "인터넷", "해킹", "개인정보", "신고", "상담"),
    "1339": ("질병", "감염병", "응급의료", "상담"),
    "182": ("경찰민원", "민원", "경찰"),
    "125": ("밀수", "관세", "신고"),
    "129": ("보건복지", "상담"),
    "1388": ("청소년", "상담"),
    "1399": ("식품", "안전", "신고"),
}

_PUBLIC_DIGITS = {**SINO_DIGITS, 0: "공"}
PUBLIC_NUMBER_READINGS = {
    number: "".join(_PUBLIC_DIGITS[int(digit)] for digit in number)
    for number in PUBLIC_NUMBER_CONTEXTS
}

_PUBLIC_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:110|120|117|118|1339|182|125|129|1388|1399)(?![A-Za-z0-9])"
)


def scan_public_number_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []
    sanitized = _mask_ranges(raw_text, excluded_ranges)
    candidates: list[SurfaceCandidate] = []
    for match in _PUBLIC_NUMBER_RE.finditer(sanitized):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        if span.end < len(raw_text) and raw_text[span.end] in "([":
            continue
        gate = evaluate_public_number_gate(sanitized, span, raw_text[span.start : span.end])
        if gate["decision"] != "pass":
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=SourceSpan(span.start, int(gate["tail_end"])),
                owner="public_number",
                surface_type="PUBLIC_NUMBER_SURFACE",
                reason=gate["reason"],
                metadata={
                    "tail": gate["tail"],
                    "reading": PUBLIC_NUMBER_READINGS[match.group(0)],
                    "gate_reason": gate["reason"],
                },
            )
        )
    return candidates


def evaluate_public_number_gate(
    raw_text: str, span: SourceSpan, number: str
) -> dict[str, str | int]:
    contexts = PUBLIC_NUMBER_CONTEXTS.get(number)
    if contexts is None:
        return {"decision": "fail", "reason": "unsupported_public_number"}
    tail_info = _allowed_tail_at(raw_text, span.end)
    if tail_info is None:
        return {"decision": "fail", "reason": "disallowed_tail"}
    tail, tail_end = tail_info
    if not has_public_number_context(raw_text, span, number):
        return {
            "decision": "fail",
            "reason": "missing_context",
            "tail": tail,
            "tail_end": tail_end,
        }
    return {
        "decision": "pass",
        "reason": "public_number_context_gate",
        "tail": tail,
        "tail_end": tail_end,
    }


def parse_public_number_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "public_number":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def is_public_number(raw: str) -> bool:
    return raw in PUBLIC_NUMBER_READINGS


def has_public_number_context(raw_text: str, span: SourceSpan, number: str) -> bool:
    contexts = PUBLIC_NUMBER_CONTEXTS[number]
    prev_text = raw_text[max(0, span.start - 16) : span.start]
    next_text = raw_text[span.end : min(len(raw_text), span.end + 16)]
    return any(context in prev_text or context in next_text for context in contexts)


def build_public_number_gate_logs(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[TraceLogEntry]:
    if excluded_ranges is None:
        excluded_ranges = []
    sanitized = _mask_ranges(raw_text, excluded_ranges)
    logs: list[TraceLogEntry] = []
    for match in _PUBLIC_NUMBER_RE.finditer(sanitized):
        span = SourceSpan(match.start(), match.end())
        if _span_overlaps_excluded_range(span, excluded_ranges):
            continue
        raw = raw_text[span.start : span.end]
        if span.end < len(raw_text) and raw_text[span.end] in "([":
            gate = {"decision": "fail", "reason": "context_boundary_block"}
        else:
            gate = evaluate_public_number_gate(sanitized, span, raw)
        logs.append(
            TraceLogEntry(
                stage="public_number_gate",
                event="public_number_context_gate",
                span=span,
                raw=raw,
                owner="public_number",
                decision=str(gate["decision"]),
                reason=str(gate["reason"]),
                action="allow_public_number_parse"
                if gate["decision"] == "pass"
                else "number_fallback",
                metadata={"tail": gate.get("tail")},
            )
        )
    return logs


def _allowed_tail_at(raw_text: str, start: int) -> tuple[str, int] | None:
    if start < len(raw_text) and raw_text[start] in "([":
        return None
    remainder = raw_text[start:]
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
    "PUBLIC_NUMBER_CONTEXTS",
    "PUBLIC_NUMBER_READINGS",
    "build_public_number_gate_logs",
    "evaluate_public_number_gate",
    "has_public_number_context",
    "is_public_number",
    "parse_public_number_candidate",
    "scan_public_number_candidates",
]
