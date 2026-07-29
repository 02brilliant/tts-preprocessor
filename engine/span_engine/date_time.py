from __future__ import annotations

import calendar
import re

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import native_number_under_100
from engine.span_engine.delimiters import COLON_LIKE_DELIMITERS
from engine.span_engine.models import SourceSpan, SurfaceCandidate, TraceLogEntry
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.numeric_reading import read_sino_time_suffix_number_text
from engine.span_engine.numeric_suffix import (
    starts_with_longer_registered_numeric_suffix,
)
from engine.span_engine.sentence_final_slash import is_sentence_final_slash_boundary

_DATE_SEP_RE = re.compile(r"(?<![A-Za-z0-9])(\d{4})([-/.／])(\d{2})\2(\d{2})(?![A-Za-z0-9])")
_SHORT_DOTTED_CODE_RE = re.compile(r"(?<![A-Za-z0-9.])(\d{4})\.(\d{1,2})(?![A-Za-z0-9.])")
_KOREAN_YMD_RE = re.compile(r"(?<![A-Za-z0-9가-힣])(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일")
_KOREAN_YM_RE = re.compile(r"(?<![A-Za-z0-9가-힣])(\d{4})년\s*(\d{1,2})월")
_KOREAN_MD_RE = re.compile(r"(?<![A-Za-z0-9가-힣])(\d{1,2})월\s*(\d{1,2})일")
_KOREAN_YEAR_RE = re.compile(r"(?<![A-Za-z0-9가-힣])(\d{4})년")
_KOREAN_MONTH_RE = re.compile(r"(?<![A-Za-z0-9가-힣])(\d{1,2})월")

_COLON_LIKE_RE_CLASS = "".join(re.escape(ch) for ch in COLON_LIKE_DELIMITERS)
_COLON_TIME_RE = re.compile(
    rf"(?<![A-Za-z0-9])(\d{{1,2}})[{_COLON_LIKE_RE_CLASS}](\d{{2}})(?![A-Za-z0-9])"
)
_ANY_COLON_TIME_RE = re.compile(
    rf"(?<![A-Za-z0-9])\d{{1,2}}[{_COLON_LIKE_RE_CLASS}]\d{{2}}"
    rf"(?:[{_COLON_LIKE_RE_CLASS}]\d{{2}})?(?![A-Za-z0-9])"
)
_KOREAN_SUFFIX_INTEGER_RE = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_KOREAN_SUFFIX_NUMBER_RE = rf"(?:{_KOREAN_SUFFIX_INTEGER_RE})(?:\.\d+)?"
_KOREAN_TIME_RE = re.compile(
    rf"(?<![A-Za-z0-9가-힣])(\d+)시(?!간)"
    rf"(?:[ \t]*({_KOREAN_SUFFIX_NUMBER_RE})[ \t]*분"
    rf"(?:[ \t]*({_KOREAN_SUFFIX_NUMBER_RE})[ \t]*초)?)?"
)
_KOREAN_MINUTE_SECOND_RE = re.compile(
    rf"(?<![A-Za-z0-9가-힣])({_KOREAN_SUFFIX_NUMBER_RE})[ \t]*분"
    rf"[ \t]*({_KOREAN_SUFFIX_NUMBER_RE})[ \t]*초"
)
_KOREAN_MINUTE_OR_SECOND_RE = re.compile(
    rf"(?<![A-Za-z0-9가-힣])({_KOREAN_SUFFIX_NUMBER_RE})[ \t]*(?:분|초)"
)

TIME_PREFIXES = ("오전", "오후", "새벽", "아침", "정오", "밤", "저녁", "AM", "PM", "am", "pm")
TIME_POSTPOSITIONS = ("에", "까지", "부터", "경", "쯤", "정각")
KOREAN_TIME_SAFE_TAILS = tuple(
    sorted(
        (
            "이었다",
            "이었고",
            "이라면",
            "이지만",
            "입니다",
            "에는",
            "에서",
            "에도",
            "이라고",
            "인데",
            "였다",
            "였고",
            "이다",
            "이면",
            "이며",
            "이고",
            "면",
            "라면",
            "라고",
            "인",
            "으로",
            "보다",
            "처럼",
            "부터",
            "까지",
            "경",
            "쯤",
            "정각",
            "다",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "로",
            "와",
            "과",
            "도",
            "만",
            "에",
            "마다",
        ),
        key=len,
        reverse=True,
    )
)
TIME_TITLE_SUFFIXES = ("뉴스",)
TIME_EVENT_KEYWORDS = (
    "출발",
    "도착",
    "시작",
    "종료",
    "마감",
    "개시",
    "오픈",
    "폐장",
    "예약",
    "탑승",
    "발차",
    "상영",
    "회의",
    "수업",
    "진료",
    "시각",
)
DATE_CONTEXT_KEYWORDS = ("오늘", "내일", "어제", "모레", "다음날", "당일")
TIME_LIST_CONTEXT_KEYWORDS = TIME_EVENT_KEYWORDS + (
    "시간",
    "일정",
    "시간표",
    "편성표",
    "알림",
    "예약시간",
    "시작시간",
    "종료시간",
)
SCORE_CONTEXT_KEYWORDS = (
    "score",
    "스코어",
    "점수",
    "비율",
    "화면비",
    "희석",
    "축척",
    "승리",
    "패배",
    "무승부",
    "세트",
    "대결",
    "ratio",
    "line",
    "case",
    "verse",
    "chapter",
    "라인",
)
MEDIA_DURATION_CONTEXT_KEYWORDS = ("영상", "재생시간", "타임라인")
CODE_CONTEXT_KEYWORDS = (
    "version",
    "ver",
    "log",
    "model",
    "code",
    "file",
    "id",
    "버전",
    "로그",
    "모델",
    "코드",
    "파일",
    "문서",
    "참조",
    "요한복음",
    "창세기",
    "시편",
)


def scan_date_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    consumed_spans: list[SourceSpan] = []
    for match in _DATE_SEP_RE.finditer(raw_text):
        year_raw = match.group(1)
        separator = match.group(2)
        month_raw = match.group(3)
        day_raw = match.group(4)
        year = int(year_raw)
        month = int(month_raw)
        day = int(day_raw)
        span = SourceSpan(match.start(), match.end())

        # If it looks like a date but has bad boundaries or explicit code context,
        # claim it as preserve so later decimal fallback cannot partially consume it.
        if not _valid_separator_date_boundary(raw_text, span) or _has_explicit_code_context(raw_text, span):
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="preserve",
                    surface_type="DATE_PRESERVE_SURFACE",
                    reason="date_boundary_preserve",
                )
            )
            consumed_spans.append(span)
            continue

        if not _year_in_supported_range(year):
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="preserve",
                    surface_type="DATE_PRESERVE_SURFACE",
                    reason="date_year_range_preserve",
                )
            )
            consumed_spans.append(span)
            continue

        if not is_valid_date(year, month, day):
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="date",
                    surface_type="CODE_SEPARATOR_BLOCK_SURFACE",
                    reason=f"date_{_separator_name(separator)}_yyyy_mm_dd_calendar_invalid_fallback",
                    metadata={
                        "year": year,
                        "month": month,
                        "day": day,
                        "separator": separator,
                        "fallback_owner": "code_separator_block",
                        "fallback_reason": "calendar_invalid_date_like",
                        "reading": separator_date_fallback_reading(
                            year_raw, month_raw, day_raw, separator
                        ),
                    },
                )
            )
            consumed_spans.append(span)
            continue

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="date",
                surface_type="DATE_SURFACE",
                reason=f"date_{_separator_name(separator)}_yyyy_mm_dd_gate",
                metadata={
                    "year": year,
                    "month": month,
                    "day": day,
                    "separator": separator,
                    "reading": date_number_reading(year, month, day),
                },
            )
        )
        consumed_spans.append(span)

    for match in _SHORT_DOTTED_CODE_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if _overlaps_any(span, consumed_spans):
            continue
        if not _has_explicit_code_context(raw_text, span):
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="DATE_PRESERVE_SURFACE",
                reason="short_dotted_code_context_preserve",
            )
        )
        consumed_spans.append(span)

    for regex, builder in (
        (_KOREAN_YMD_RE, _korean_ymd_candidates),
        (_KOREAN_YM_RE, _korean_ym_candidates),
        (_KOREAN_MD_RE, _korean_md_candidates),
        (_KOREAN_YEAR_RE, _korean_year_candidates),
        (_KOREAN_MONTH_RE, _korean_month_candidates),
    ):
        for match in regex.finditer(raw_text):
            span = SourceSpan(match.start(), match.end())
            if not _valid_korean_date_boundary(raw_text, span):
                continue
            if _overlaps_any(span, consumed_spans):
                continue
            built = builder(match)
            if built is None:
                consumed_spans.append(span)
                continue
            candidates.extend(built)
            consumed_spans.append(span)
    return candidates


def scan_time_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []
    
    sanitized = _mask_ranges(raw_text, excluded_ranges)
    candidates: list[SurfaceCandidate] = []
    colon_matches = list(_COLON_TIME_RE.finditer(sanitized))
    multiple_colon_times = len(colon_matches) > 1
    time_list_spans = _comma_time_list_context_spans(sanitized, colon_matches)
    for match in colon_matches:
        span = SourceSpan(match.start(), match.end())
        if _is_part_of_seconds_time(sanitized, span):
            continue
        span_key = (span.start, span.end)
        if multiple_colon_times and span_key not in time_list_spans:
            continue
        hour = int(match.group(1))
        minute = int(match.group(2))
        if span_key in time_list_spans:
            gate = {
                "decision": "pass",
                "reason": "time_list_context",
                "raw": sanitized[span.start : span.end],
            }
        else:
            gate = evaluate_time_colon_gate(
                sanitized, span, hour, minute, strong_context_text=raw_text
            )
        if gate["decision"] != "pass":
            continue
        reading = time_number_reading(hour, minute)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="time",
                surface_type="TIME_SURFACE",
                reason=gate["reason"],
                metadata={
                    "hour": hour,
                    "minute": minute,
                    "reading": reading,
                    "gate_reason": gate["reason"],
                },
            )
        )

    korean_time_matches = list(_KOREAN_TIME_RE.finditer(raw_text))
    korean_minute_second_matches = list(
        _KOREAN_MINUTE_SECOND_RE.finditer(raw_text)
    )
    compound_spans = [
        SourceSpan(match.start(), match.end())
        for match in (*korean_time_matches, *korean_minute_second_matches)
    ]
    candidates.extend(
        _unsafe_korean_suffix_amount_candidates(raw_text, compound_spans)
    )
    for match in korean_time_matches:
        candidates.extend(_korean_time_candidates(raw_text, match))
    for match in korean_minute_second_matches:
        if any(
            time_match.start() <= match.start()
            and match.end() <= time_match.end()
            for time_match in korean_time_matches
        ):
            continue
        candidates.extend(_korean_minute_second_candidates(raw_text, match))
    return candidates


def parse_date_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "date":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def parse_time_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner != "time":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def is_valid_date(year: int, month: int, day: int) -> bool:
    if not all(isinstance(value, int) for value in (year, month, day)):
        raise TypeError("year, month, day must be int")
    if year < 1900 or year > 2099:
        return False
    if month < 1 or month > 12:
        return False
    return 1 <= day <= calendar.monthrange(year, month)[1]


def _year_in_supported_range(year: int) -> bool:
    return 1900 <= year <= 2099


def dotted_date_fallback_reading(year: str, month: str, day: str) -> str:
    return f"{_digit_block_reading(year)}쩜 {_digit_block_reading(month)}쩜 {_digit_block_reading(day)}"


def separator_date_fallback_reading(year: str, month: str, day: str, separator: str) -> str:
    if separator == ".":
        return dotted_date_fallback_reading(year, month, day)
    return f"{_digit_block_reading(year)} {_digit_block_reading(month)} {_digit_block_reading(day)}"


def is_valid_time(hour: int, minute: int, second: int | None = None) -> bool:
    if not isinstance(hour, int) or not isinstance(minute, int):
        raise TypeError("hour and minute must be int")
    if hour < 0 or hour > 24 or minute < 0 or minute > 59:
        return False
    if second is not None and (not isinstance(second, int) or second < 0 or second > 59):
        return False
    return True


def is_valid_korean_clock_time(
    hour: int, minute: int | None = None, second: int | None = None
) -> bool:
    if not isinstance(hour, int):
        raise TypeError("hour must be int")
    if hour < 0 or hour > 24:
        return False
    if minute is not None and (not isinstance(minute, int) or minute < 0 or minute > 59):
        return False
    if second is not None and (not isinstance(second, int) or second < 0 or second > 59):
        return False
    return True


def date_number_reading(year: int, month: int, day: int | None = None) -> str:
    year_reading = f"{number_to_korean_under_10000(year)}년"
    month_reading = f"{_month_reading(month)}월"
    if day is None:
        return f"{year_reading} {month_reading}"
    day_reading = f"{number_to_korean_under_10000(day)}일"
    return f"{year_reading} {month_reading} {day_reading}"


def time_number_reading(hour: int, minute: int, second: int | None = None) -> str:
    hour_reading = clock_hour_reading(hour) or number_to_korean_under_10000(hour)
    reading = f"{hour_reading}시"
    if minute != 0:
        reading += f" {number_to_korean_under_10000(minute)}분"
    if second is not None:
        reading += f" {number_to_korean_under_10000(second)}초"
    return reading


def clock_hour_reading(hour: int) -> str | None:
    if not isinstance(hour, int):
        raise TypeError("hour must be int")
    if hour == 0:
        return "영"
    if 1 <= hour <= 12:
        return native_number_under_100(hour)
    if 13 <= hour <= 24:
        return number_to_korean_under_10000(hour)
    return None


def evaluate_time_colon_gate(
    raw_text: str,
    candidate_span: SourceSpan,
    hour: int,
    minute: int,
    strong_context_text: str | None = None,
) -> dict[str, str]:
    raw = raw_text[candidate_span.start : candidate_span.end]
    if _score_or_ratio_context(raw_text, candidate_span):
        return {"decision": "fail", "reason": "score_context", "raw": raw}
    if _media_duration_context(raw_text, candidate_span):
        return {"decision": "fail", "reason": "media_duration_context", "raw": raw}
    next_text = raw_text[candidate_span.end :]
    prev_text = raw_text[: candidate_span.start]
    prefix = _time_prefix(prev_text)
    if _has_explicit_code_context(raw_text, candidate_span):
        return {"decision": "fail", "reason": "code_context", "raw": raw}
    if prefix is not None and not (1 <= hour <= 12):
        return {"decision": "fail", "reason": "time_prefix_hour_range", "raw": raw}
    if not is_valid_time(hour, minute):
        return {"decision": "fail", "reason": "invalid_time", "raw": raw}
    hour_text, minute_text = re.split("[:：]", raw, maxsplit=1)
    if is_strong_time_like_colon(hour_text, minute_text) and _valid_strong_time_like_context(
        strong_context_text or raw_text, candidate_span
    ):
        return {"decision": "pass", "reason": "strong_time_like_bare", "raw": raw}
    if raw_text == raw:
        return {"decision": "fail", "reason": "bare_time_preserve", "raw": raw}
    if next_text.startswith(TIME_POSTPOSITIONS) or next_text.startswith("입니다"):
        return {"decision": "pass", "reason": "time_postposition", "raw": raw}
    if prefix is not None:
        return {"decision": "pass", "reason": "time_prefix", "raw": raw}
    has_ctx = _has_context_nearby(prev_text, next_text)
    if has_ctx:
        return {"decision": "pass", "reason": "time_event_context", "raw": raw}
    return {"decision": "fail", "reason": "time_context_missing", "raw": raw}


def is_strong_time_like_colon(hour_text: str, minute_text: str) -> bool:
    if not hour_text.isdigit() or not minute_text.isdigit():
        return False
    if not (1 <= len(hour_text) <= 2) or len(minute_text) != 2:
        return False
    hour = int(hour_text)
    minute = int(minute_text)
    if not is_valid_time(hour, minute):
        return False
    return (len(hour_text) == 2 and hour_text.startswith("0")) or 0 <= minute <= 9


def _valid_strong_time_like_context(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char in {"+", "-"}:
        return False
    if next_char is None or next_char.isspace():
        return True
    if next_char in {".", ",", "!", "?", ";", ":", "。", "，", "！", "？"}:
        return True
    return False


def _comma_time_list_context_spans(
    raw_text: str, matches: list[re.Match[str]]
) -> set[tuple[int, int]]:
    if len(matches) < 2:
        return set()
    allowed: set[tuple[int, int]] = set()
    group: list[re.Match[str]] = []
    previous: re.Match[str] | None = None
    for match in matches:
        if previous is None:
            group = [match]
        elif _is_comma_time_list_delimiter(raw_text[previous.end() : match.start()]):
            group.append(match)
        else:
            allowed.update(_allowed_time_list_group_spans(raw_text, group))
            group = [match]
        previous = match
    allowed.update(_allowed_time_list_group_spans(raw_text, group))
    return allowed


def _allowed_time_list_group_spans(
    raw_text: str, group: list[re.Match[str]]
) -> set[tuple[int, int]]:
    if len(group) < 2 or not _valid_time_list_group(raw_text, group):
        return set()
    if not _has_explicit_time_list_context(raw_text, group):
        return set()
    return {(match.start(), match.end()) for match in group}


def _valid_time_list_group(raw_text: str, group: list[re.Match[str]]) -> bool:
    for match in group:
        span = SourceSpan(match.start(), match.end())
        if _is_part_of_seconds_time(raw_text, span):
            return False
        if _score_or_ratio_context(raw_text, span):
            return False
        if _media_duration_context(raw_text, span):
            return False
        if _has_explicit_code_context(raw_text, span):
            return False
        if not is_valid_time(int(match.group(1)), int(match.group(2))):
            return False
    return True


def _has_explicit_time_list_context(
    raw_text: str, group: list[re.Match[str]]
) -> bool:
    first = group[0]
    last = group[-1]
    segment_start = _time_list_segment_start(raw_text, first.start())
    segment_end = _time_list_segment_end(raw_text, last.end())
    segment = raw_text[segment_start:segment_end]
    if _has_time_list_keyword_context(segment):
        return True
    if _has_direct_time_list_prefix(raw_text, first):
        return True
    if raw_text[last.end() :].startswith(TIME_POSTPOSITIONS):
        return True
    return _has_preceding_korean_time_list_context(
        raw_text, segment_start, first.start()
    )


def _is_comma_time_list_delimiter(text: str) -> bool:
    return re.fullmatch(r"\s*[,，]\s*", text) is not None


def _time_list_segment_start(raw_text: str, start: int) -> int:
    index = start - 1
    while index >= 0:
        if raw_text[index] in ".!?;。！？\n\r":
            return index + 1
        index -= 1
    return 0


def _time_list_segment_end(raw_text: str, end: int) -> int:
    index = end
    while index < len(raw_text):
        if raw_text[index] in ".!?;。！？\n\r":
            return index
        index += 1
    return len(raw_text)


def _has_time_list_keyword_context(text: str) -> bool:
    for keyword in sorted(TIME_LIST_CONTEXT_KEYWORDS, key=len, reverse=True):
        start = text.find(keyword)
        while start != -1:
            end = start + len(keyword)
            if _valid_time_list_keyword_tail(text[end:]):
                return True
            start = text.find(keyword, start + 1)
    return False


def _valid_time_list_keyword_tail(text: str) -> bool:
    if not text:
        return True
    if text[0].isspace() or text[0] in {",", "，", ".", "!", "?", ";"}:
        return True
    return text.startswith(
        (
            "은",
            "는",
            "을",
            "를",
            "이",
            "가",
            "에",
            "의",
            "로",
            "으로",
            "부터",
            "까지",
            "에서",
            "입니다",
            "이다",
        )
    )


def _has_direct_time_list_prefix(raw_text: str, first: re.Match[str]) -> bool:
    prefix = _time_prefix(raw_text[: first.start()])
    if prefix is None:
        return False
    return 1 <= int(first.group(1)) <= 12


def _has_preceding_korean_time_list_context(
    raw_text: str, segment_start: int, list_start: int
) -> bool:
    left = raw_text[segment_start:list_start]
    for match in reversed(list(_KOREAN_TIME_RE.finditer(left))):
        if _is_comma_time_list_delimiter(left[match.end() :]):
            return True
        break
    return False


def build_time_gate_logs(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[TraceLogEntry]:
    if excluded_ranges is None:
        excluded_ranges = []
    sanitized = _mask_ranges(raw_text, excluded_ranges)
    logs: list[TraceLogEntry] = []
    matches = list(_COLON_TIME_RE.finditer(sanitized))
    multiple = len(matches) > 1
    time_list_spans = _comma_time_list_context_spans(sanitized, matches)
    for match in matches:
        span = SourceSpan(match.start(), match.end())
        raw = raw_text[span.start : span.end]
        span_key = (span.start, span.end)
        if _is_part_of_seconds_time(sanitized, span):
            decision = {"decision": "fail", "reason": "seconds_time_unsupported", "raw": raw}
        elif multiple and span_key in time_list_spans:
            decision = {"decision": "pass", "reason": "time_list_context", "raw": raw}
        elif multiple:
            decision = {"decision": "fail", "reason": "multiple_time_candidates", "raw": raw}
        else:
            decision = evaluate_time_colon_gate(
                sanitized, span, int(match.group(1)), int(match.group(2))
            )
        logs.append(
            TraceLogEntry(
                stage="time_gate",
                event="time_colon_gate",
                span=span,
                raw=raw,
                owner="time",
                decision=decision["decision"],
                reason=decision["reason"],
                action="allow_time_parse" if decision["decision"] == "pass" else "preserve",
            )
        )
    return logs


def _korean_ymd_candidates(match: re.Match[str]) -> list[SurfaceCandidate] | None:
    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    if not is_valid_date(year, month, day):
        return None
    return [
        _numeric_marker_candidate(match, 1, "date_korean_year_month_day_gate", year),
        _numeric_marker_candidate(
            match,
            2,
            "date_korean_year_month_day_gate",
            month,
            reading=_korean_date_component_reading(
                match, 2, _month_reading(month)
            ),
        ),
        _numeric_marker_candidate(
            match,
            3,
            "date_korean_year_month_day_gate",
            day,
            reading=_korean_date_component_reading(
                match, 3, number_to_korean_under_10000(day)
            ),
        ),
    ]


def _korean_ym_candidates(match: re.Match[str]) -> list[SurfaceCandidate] | None:
    year = int(match.group(1))
    month = int(match.group(2))
    if year < 1900 or year > 2099 or month < 1 or month > 12:
        return None
    return [
        _numeric_marker_candidate(match, 1, "date_korean_year_month_gate", year),
        _numeric_marker_candidate(
            match,
            2,
            "date_korean_year_month_gate",
            month,
            reading=_korean_date_component_reading(
                match, 2, _month_reading(month)
            ),
        ),
    ]


def _korean_md_candidates(match: re.Match[str]) -> list[SurfaceCandidate] | None:
    month = int(match.group(1))
    day = int(match.group(2))
    if month < 1 or month > 12:
        return None
    if day < 1 or day > calendar.monthrange(2024, month)[1]:
        return None
    return [
        _numeric_marker_candidate(
            match,
            1,
            "date_korean_month_day_gate",
            month,
            reading=_month_reading(month),
        ),
        _numeric_marker_candidate(
            match,
            2,
            "date_korean_month_day_gate",
            day,
            reading=_korean_date_component_reading(
                match, 2, number_to_korean_under_10000(day)
            ),
        ),
    ]


def _korean_year_candidates(match: re.Match[str]) -> list[SurfaceCandidate] | None:
    year = int(match.group(1))
    if year < 1900 or year > 2099:
        return None
    return [_numeric_marker_candidate(match, 1, "date_korean_year_gate", year)]


def _korean_month_candidates(match: re.Match[str]) -> list[SurfaceCandidate] | None:
    month = int(match.group(1))
    if month < 1 or month > 12:
        return None
    reading = number_to_korean_under_10000(month)
    if not match.string.startswith("개", match.end()):
        reading = _month_reading(month)
    return [
        _numeric_marker_candidate(
            match, 1, "date_korean_month_gate", month, reading=reading
        )
    ]


def _korean_time_candidates(
    raw_text: str, match: re.Match[str]
) -> list[SurfaceCandidate]:
    hour_text = match.group(1)
    normalized_hour_text = hour_text.lstrip("0") or "0"
    hour = (
        int(normalized_hour_text)
        if len(normalized_hour_text) <= 2
        else 25
    )
    minute_raw = match.group(2)
    second_raw = match.group(3)
    minute_reading = (
        _korean_minute_second_reading(minute_raw)
        if minute_raw is not None
        else None
    )
    second_reading = (
        _korean_minute_second_reading(second_raw)
        if second_raw is not None
        else None
    )
    if (minute_raw is not None and minute_reading is None) or (
        second_raw is not None and second_reading is None
    ):
        return _preserve_numeric_groups(
            match, "invalid_korean_time_suffix_numeric_preserve"
        )
    span = SourceSpan(match.start(), match.end())
    if not is_valid_korean_clock_time(hour):
        return _preserve_numeric_groups(match, "invalid_korean_time_preserve")
    valid_boundary = _valid_korean_time_boundary(raw_text, span)
    if (
        not valid_boundary
        and minute_raw is not None
        and _has_structured_time_approximate_tail(raw_text, span.end)
    ):
        valid_boundary = True
    if not valid_boundary:
        if (
            minute_raw is None
            and second_raw is None
            and _starts_with_time_title_suffix(raw_text, span.end)
        ):
            return [
                _numeric_marker_candidate(
                    match,
                    1,
                    "time_hour_broadcast_title_suffix",
                    hour,
                    owner="time",
                    reading=clock_hour_reading(hour),
                )
            ]
        prev_char = raw_text[span.start - 1] if span.start > 0 else None
        if prev_char in {"~", "∼", "～", "〜"}:
            return []
        return _preserve_numeric_groups(match, "attached_korean_time_preserve")
    candidates = [
        _numeric_marker_candidate(
            match,
            1,
            "time_hour_korean_context",
            hour,
            owner="time",
            reading=f"{clock_hour_reading(hour)} ",
            core_span=SourceSpan(
                match.start(1), _unit_start_after_group(match, 1, "시")
            ),
        )
    ]
    if minute_raw is not None:
        assert minute_reading is not None
        candidates.append(
            _numeric_marker_candidate(
                match,
                2,
                "time_minute_korean_context",
                minute_raw,
                owner="time",
                reading=(
                    f"{_generated_component_separator(match, 1, 2, '시')}"
                    f"{minute_reading}"
                ),
            )
        )
    if second_raw is not None:
        assert second_reading is not None
        candidates.append(
            _numeric_marker_candidate(
                match,
                3,
                "time_second_korean_context",
                second_raw,
                owner="time",
                reading=(
                    f"{_generated_component_separator(match, 2, 3, '분')}"
                    f"{second_reading}"
                ),
            )
        )
    return candidates


def _unsafe_korean_suffix_amount_candidates(
    raw_text: str, compound_spans: list[SourceSpan]
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _KOREAN_MINUTE_OR_SECOND_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if any(
            compound.start <= span.start and span.end <= compound.end
            for compound in compound_spans
        ):
            continue
        if _is_existing_duration_fraction_or_negative(raw_text, span):
            continue
        short_suffix = raw_text[span.end - 1 : span.end]
        if starts_with_longer_registered_numeric_suffix(
            raw_text,
            span.end - len(short_suffix),
            short_suffix,
        ):
            continue
        if _valid_korean_suffix_amount_boundary(raw_text, span):
            continue
        preserve_span = SourceSpan(
            span.start, _korean_suffix_like_token_end(raw_text, span.end)
        )
        candidates.append(
            SurfaceCandidate(
                core_span=preserve_span,
                full_span=preserve_span,
                owner="preserve",
                surface_type="TIME_PRESERVE_SURFACE",
                reason="unsafe_korean_minute_second_suffix_preserve",
            )
        )
    return candidates


def _is_existing_duration_fraction_or_negative(
    raw_text: str, span: SourceSpan
) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    if prev_char in {"~", "∼", "～", "〜"}:
        return span.start >= 2 and raw_text[span.start - 2].isdigit()
    if not raw_text.startswith("분", span.end - 1):
        return False
    if prev_char == "-":
        return True
    if prev_char != "/" or span.start < 2:
        return False
    numerator_end = span.start - 1
    numerator_start = numerator_end
    while numerator_start > 0 and raw_text[numerator_start - 1].isdigit():
        numerator_start -= 1
    return numerator_start < numerator_end


def _korean_minute_second_candidates(
    raw_text: str, match: re.Match[str]
) -> list[SurfaceCandidate]:
    minute_raw = match.group(1)
    second_raw = match.group(2)
    minute_reading = _korean_minute_second_reading(minute_raw)
    second_reading = _korean_minute_second_reading(second_raw)
    span = SourceSpan(match.start(), match.end())
    if minute_reading is None or second_reading is None:
        return _preserve_numeric_groups(
            match, "invalid_korean_minute_second_preserve"
        )
    valid_boundary = _valid_korean_time_boundary(raw_text, span)
    if (
        not valid_boundary
        and _has_structured_time_approximate_tail(raw_text, span.end)
    ):
        valid_boundary = True
    if not valid_boundary:
        return _preserve_numeric_groups(
            match, "attached_korean_minute_second_preserve"
        )
    return [
        _numeric_marker_candidate(
            match,
            1,
            "time_minute_korean_compound",
            minute_raw,
            owner="time",
            reading=minute_reading,
        ),
        _numeric_marker_candidate(
            match,
            2,
            "time_second_korean_compound",
            second_raw,
            owner="time",
            reading=(
                f"{_generated_component_separator(match, 1, 2, '분')}"
                f"{second_reading}"
            ),
        ),
    ]


def _korean_minute_second_reading(raw: str | None) -> str | None:
    if raw is None:
        return None
    return read_sino_time_suffix_number_text(raw)


def _generated_component_separator(
    match: re.Match[str],
    previous_group: int,
    current_group: int,
    previous_unit: str,
) -> str:
    previous_marker_end = (
        _unit_start_after_group(match, previous_group, previous_unit)
        + len(previous_unit)
    )
    return " " if match.start(current_group) == previous_marker_end else ""


def _unit_start_after_group(
    match: re.Match[str], group: int, unit: str
) -> int:
    unit_start = match.string.find(unit, match.end(group), match.end())
    if unit_start < 0:
        raise ValueError(f"missing {unit!r} marker after regex group {group}")
    return unit_start


def _preserve_numeric_groups(match: re.Match[str], reason: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for group in range(1, match.re.groups + 1):
        if match.group(group) is None:
            continue
        span = SourceSpan(match.start(group), match.end(group))
        raw = match.group(group)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=SourceSpan(match.start(), match.end()),
                owner="time",
                surface_type="TIME_PRESERVE_SURFACE",
                reason=reason,
                metadata={"reading": raw, "preserve": True},
            )
        )
    return candidates


def _numeric_marker_candidate(
    match: re.Match[str],
    group: int,
    reason: str,
    value: int | str,
    owner: str = "date",
    reading: str | None = None,
    core_span: SourceSpan | None = None,
) -> SurfaceCandidate:
    span = core_span or SourceSpan(match.start(group), match.end(group))
    if reading is None:
        if not isinstance(value, int):
            raise TypeError("non-integer marker values require an explicit reading")
        reading = number_to_korean_under_10000(value)
    return SurfaceCandidate(
        core_span=span,
        full_span=SourceSpan(match.start(), match.end()),
        owner=owner,
        surface_type="DATE_SURFACE" if owner == "date" else "TIME_SURFACE",
        reason=reason,
        metadata={"value": value, "reading": reading},
    )


def _month_reading(month: int) -> str:
    if month == 6:
        return "유"
    if month == 10:
        return "시"
    return number_to_korean_under_10000(month)


def _korean_date_component_reading(
    match: re.Match[str], group: int, reading: str
) -> str:
    if match.string[match.start(group) - 1].isspace():
        return reading
    return f" {reading}"


def _valid_separator_date_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None and (prev_char.isalnum() or prev_char in {"-", "/", "／", ".", "~", "∼"}):
        return False
    if next_char is None:
        return True
    if next_char.isascii() and (next_char.isalnum() or next_char in {"-", "/", ".", "~"}):
        return False
    if next_char in {"-", "/", "／", ".", "~"}:
        return False
    return True


def _has_explicit_code_context(raw_text: str, span: SourceSpan) -> bool:
    left = raw_text[: span.start].rstrip()
    if not left:
        return False
    return left.split()[-1].lower() in CODE_CONTEXT_KEYWORDS


def _separator_name(separator: str) -> str:
    if separator == "-":
        return "hyphen"
    if separator in {"/", "／"}:
        return "slash"
    if separator == ".":
        return "dotted"
    return "separator"


def _digit_block_reading(block: str) -> str:
    readings = {
        "0": "공",
        "1": "일",
        "2": "이",
        "3": "삼",
        "4": "사",
        "5": "오",
        "6": "육",
        "7": "칠",
        "8": "팔",
        "9": "구",
    }
    return "".join(readings[digit] for digit in block)


def _valid_korean_date_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    if prev_char is None:
        return True
    if prev_char in {"~", "∼", "～", "〜", "-", "/", "."}:
        return False
    if prev_char.isascii() and prev_char.isalnum():
        return False
    return True


def _valid_korean_time_boundary(raw_text: str, span: SourceSpan) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char in {
        "~",
        "∼",
        "～",
        "〜",
        "-",
        "+",
        "/",
        ".",
        ":",
        "_",
        "·",
    }:
        return False
    if prev_char is not None and (prev_char.isascii() and prev_char.isalnum()):
        return False
    if prev_char is not None and "\uac00" <= prev_char <= "\ud7a3":
        return False
    if next_char is None:
        return True
    if next_char == "/":
        return is_sentence_final_slash_boundary(raw_text, span.end)
    if next_char.isascii():
        if next_char.isalnum() or next_char in {"+", "-", "_"}:
            return False
        if (
            next_char == "."
            and span.end + 1 < len(raw_text)
            and raw_text[span.end + 1].isdigit()
        ):
            return False
    if "\uac00" <= next_char <= "\ud7a3":
        next_text = raw_text[span.end :]
        return _has_safe_korean_time_tail(next_text)
    return True


def _valid_korean_suffix_amount_boundary(
    raw_text: str, span: SourceSpan
) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in {
            "~",
            "∼",
            "～",
            "〜",
            "-",
            "+",
            "/",
            ".",
            ":",
            "_",
            "·",
        }:
            return False
    if next_char is None or next_char.isspace():
        return True
    if next_char == "/":
        return is_sentence_final_slash_boundary(raw_text, span.end)
    if next_char in {
        ",",
        "!",
        "?",
        ";",
        ":",
        ")",
        "]",
        "}",
        "。",
        "，",
        "！",
        "？",
    }:
        return True
    if next_char == ".":
        return not (
            span.end + 1 < len(raw_text)
            and raw_text[span.end + 1].isdigit()
        )
    if next_char.isascii():
        return False
    if "\uac00" <= next_char <= "\ud7a3":
        return _has_safe_korean_duration_suffix_tail(raw_text[span.end :])
    return True


def _has_safe_korean_duration_suffix_tail(next_text: str) -> bool:
    return _has_safe_korean_time_tail(next_text) or any(
        next_text.startswith(tail) for tail in ("간", "씩", "짜리")
    )


def _has_structured_time_approximate_tail(raw_text: str, start: int) -> bool:
    if not raw_text.startswith("께", start):
        return False
    end = start + 1
    if end >= len(raw_text):
        return True
    next_char = raw_text[end]
    if next_char.isspace():
        return True
    if next_char in {".", ",", "!", "?", ";", ":", "。", "，", "！", "？"}:
        return True
    if next_char == "/":
        return is_sentence_final_slash_boundary(raw_text, end)
    return False


def _korean_suffix_like_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if char.isspace() or char in {
            ",",
            "!",
            "?",
            ";",
            ":",
            ")",
            "]",
            "}",
            "。",
            "，",
            "！",
            "？",
        }:
            break
        if char == "." and (
            index + 1 >= len(raw_text)
            or (
                not raw_text[index + 1].isdigit()
                and raw_text[index + 1] != "."
            )
        ):
            break
        index += 1
    return index


def _has_safe_korean_time_tail(next_text: str) -> bool:
    for tail in KOREAN_TIME_SAFE_TAILS:
        if not next_text.startswith(tail):
            continue
        tail_end = len(tail)
        if tail_end >= len(next_text):
            return True
        next_char = next_text[tail_end]
        if next_char.isspace():
            return True
        if next_char in {".", ",", "!", "?", ";", ":", "。", "，", "！", "？"}:
            return True
        if next_char == "/" and is_sentence_final_slash_boundary(next_text, tail_end):
            return True
    return False


def _starts_with_time_title_suffix(raw_text: str, index: int) -> bool:
    for suffix in TIME_TITLE_SUFFIXES:
        if not raw_text.startswith(suffix, index):
            continue
        end = index + len(suffix)
        return _valid_time_title_suffix_tail(raw_text, end)
    return False


def _valid_time_title_suffix_tail(raw_text: str, index: int) -> bool:
    if index >= len(raw_text):
        return True
    next_char = raw_text[index]
    if next_char.isspace():
        return True
    if next_char in {".", ",", "!", "?", ";", ":", ")", "]", "}"}:
        return True
    if not _is_hangul_syllable(next_char):
        return False
    tail_end = index + 1
    while tail_end < len(raw_text) and _is_hangul_syllable(raw_text[tail_end]):
        tail_end += 1
    if tail_end >= len(raw_text):
        return True
    tail_next = raw_text[tail_end]
    if tail_next.isspace():
        return True
    if tail_next == "/" and is_sentence_final_slash_boundary(raw_text, tail_end):
        return True
    return tail_next in {".", ",", "!", "?", ";", ":", ")", "]", "}"}


def _is_hangul_syllable(value: str) -> bool:
    return "\uac00" <= value <= "\ud7a3"


def _is_part_of_seconds_time(raw_text: str, span: SourceSpan) -> bool:
    return span.end < len(raw_text) and raw_text[span.end] in {":", "："}


def _score_or_ratio_context(raw_text: str, span: SourceSpan) -> bool:
    left = raw_text[max(0, span.start - 12) : span.start].lower()
    right = raw_text[span.end : span.end + 12].lower()
    if any(keyword in left for keyword in SCORE_CONTEXT_KEYWORDS):
        return True
    if any(keyword in right for keyword in SCORE_CONTEXT_KEYWORDS):
        return True
    raw = raw_text[span.start : span.end]
    hour, minute = re.split("[:：]", raw, maxsplit=1)
    return len(hour) == 1 and len(minute) == 1


def _time_prefix(prev_text: str) -> str | None:
    compact = prev_text.rstrip()
    for prefix in TIME_PREFIXES:
        if compact.endswith(prefix):
            return prefix
    return None


def _media_duration_context(raw_text: str, span: SourceSpan) -> bool:
    left = raw_text[max(0, span.start - 12) : span.start]
    return any(keyword in left for keyword in MEDIA_DURATION_CONTEXT_KEYWORDS)


def _has_context_nearby(prev_text: str, next_text: str) -> bool:
    left = prev_text[-12:]
    right = next_text[:12]
    compact_left = left.rstrip()
    if any(compact_left.endswith(keyword) for keyword in TIME_EVENT_KEYWORDS + ("일정",)):
        return True
    if any(keyword in left for keyword in TIME_EVENT_KEYWORDS + DATE_CONTEXT_KEYWORDS):
        if right.startswith("입니다") or right.startswith(" "):
            return True
        if right.startswith(("은", "는", "을", "를", "이", "가")):
            return True
    if right.startswith(" "):
        return any(keyword in right for keyword in TIME_EVENT_KEYWORDS)
    return False


def _mask_ranges(raw_text: str, ranges: list[BracketRange]) -> str:
    chars = list(raw_text)
    for bracket_range in ranges:
        for index in range(bracket_range.span.start, bracket_range.span.end):
            chars[index] = " "
    return "".join(chars)


def _overlaps_any(span: SourceSpan, spans: list[SourceSpan]) -> bool:
    return any(span.start < other.end and other.start < span.end for other in spans)


__all__ = [
    "DATE_CONTEXT_KEYWORDS",
    "KOREAN_TIME_SAFE_TAILS",
    "SCORE_CONTEXT_KEYWORDS",
    "TIME_EVENT_KEYWORDS",
    "TIME_POSTPOSITIONS",
    "TIME_PREFIXES",
    "build_time_gate_logs",
    "date_number_reading",
    "evaluate_time_colon_gate",
    "is_strong_time_like_colon",
    "is_valid_date",
    "is_valid_time",
    "parse_date_candidate",
    "parse_time_candidate",
    "scan_date_candidates",
    "scan_time_candidates",
    "time_number_reading",
]
