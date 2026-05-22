from __future__ import annotations

import re
from typing import Protocol

from engine.parsers.numeric_date_parsers import try_parse_time

from .models import GateDecision, allow, deny


class TokenLike(Protocol):
    text: str
    start: int
    end: int


class RuleContextLike(Protocol):
    tokens: list[TokenLike]


LIKELY_SCORE_CONTEXT_PATTERN = re.compile(
    r"(?:스코어|score|전반|후반|연장|득점|승부차기|세트|게임|라운드|ratio|port|vs\.?|VS\.?)"
)
TIME_PREFIX_CONTEXT_TOKENS = ("오전", "오후", "새벽", "아침", "정오", "밤", "저녁")
TIME_EVENT_CONTEXT_TOKENS = (
    "출발", "도착", "시작", "종료", "마감", "개시", "오픈", "폐장",
    "예약", "탑승", "발차", "상영", "회의", "수업", "진료", "시각", "시간",
)
TIME_POSTPOSITION_TOKENS = ("에", "까지", "부터", "경", "쯤", "정각")
KOREAN_NUMBER_TOKEN_CORE = r"[영일이삼사오육칠팔구십백천만억조경쩜한두세네다섯여섯일곱여덟아홉열스물서른마흔쉰예순일흔여든아흔]+"
TIME_COLON_PATTERN = re.compile(
    r"(?:(?:오전|오후|새벽|아침|정오|밤|저녁)\s*)?\d{1,2}:\d{2}(?::\d{2})?"
)
TIME_VALUE_RE = re.compile(r"\d{1,2}:\d{1,2}")
KOREAN_DATE_CONTEXT_RE = re.compile(
    rf"(?:{KOREAN_NUMBER_TOKEN_CORE}년\s*{KOREAN_NUMBER_TOKEN_CORE}월\s*{KOREAN_NUMBER_TOKEN_CORE}일|{KOREAN_NUMBER_TOKEN_CORE}월\s*{KOREAN_NUMBER_TOKEN_CORE}일)$"
)


def _find_token_span(ctx: RuleContextLike, start: int, end: int) -> tuple[int | None, int | None]:
    token_start = None
    token_end = None
    for i, token in enumerate(ctx.tokens):
        if token_start is None and token.start <= start < token.end:
            token_start = i
        if token.start < end <= token.end:
            token_end = i
            break
    return token_start, token_end


def _get_prev_non_space_token(ctx: RuleContextLike, token_index: int):
    i = token_index - 1
    while i >= 0:
        token = ctx.tokens[i]
        if not token.text.isspace():
            return token
        i -= 1
    return None


def _get_next_non_space_token(ctx: RuleContextLike, token_index: int):
    i = token_index + 1
    while i < len(ctx.tokens):
        token = ctx.tokens[i]
        if not token.text.isspace():
            return token
        i += 1
    return None


def evaluate_time_colon(
    *,
    candidate: str,
    text: str,
    start: int,
    end: int,
    ctx: RuleContextLike | None,
    **_: object,
) -> GateDecision:
    if try_parse_time(candidate) is None:
        return deny("time parse failed or out of range")

    if candidate.count(":") == 2:
        return allow("hh:mm:ss is an independent clock form")

    if TIME_VALUE_RE.fullmatch(candidate) and text.strip() == candidate:
        return deny("standalone hh:mm requires positive context")

    if len(TIME_COLON_PATTERN.findall(text)) > 1:
        return deny("multiple colon time candidates in one sentence")

    window_start = max(0, start - 16)
    window_end = min(len(text), end + 16)
    if LIKELY_SCORE_CONTEXT_PATTERN.search(text[window_start:window_end]):
        return deny("score or ratio-like context near hh:mm")

    left_context = text[:start].rstrip()
    right_context = text[end:].lstrip()

    if any(left_context.endswith(prefix) for prefix in TIME_PREFIX_CONTEXT_TOKENS):
        return allow("time prefix found on the left")
    if any(right_context.startswith(postfix) for postfix in TIME_POSTPOSITION_TOKENS):
        return allow("time postposition found on the right")
    if any(token in left_context[-12:] for token in TIME_EVENT_CONTEXT_TOKENS):
        return allow("time event keyword found on the left")
    if any(token in right_context[:12] for token in TIME_EVENT_CONTEXT_TOKENS):
        return allow("time event keyword found on the right")
    if KOREAN_DATE_CONTEXT_RE.search(left_context):
        return allow("korean date context found on the left")

    if ctx is not None:
        token_start, token_end = _find_token_span(ctx, start, end)
        if token_start is not None and token_end is not None:
            prev_token = _get_prev_non_space_token(ctx, token_start)
            next_token = _get_next_non_space_token(ctx, token_end)
            if prev_token is not None and prev_token.text in TIME_PREFIX_CONTEXT_TOKENS:
                return allow("time prefix token found on the left")
            if next_token is not None and next_token.text in TIME_POSTPOSITION_TOKENS:
                return allow("time postposition token found on the right")
            if prev_token is not None and any(token in prev_token.text for token in TIME_EVENT_CONTEXT_TOKENS):
                return allow("time event token found on the left")
            if next_token is not None and any(token in next_token.text for token in TIME_EVENT_CONTEXT_TOKENS):
                return allow("time event token found on the right")

    return deny("hh:mm lacks required context gate")


def evaluate_hour_korean(
    *,
    candidate: str,
    text: str,
    start: int,
    end: int,
    ctx: RuleContextLike | None,
    **_: object,
) -> GateDecision:
    del candidate

    def _is_attached_word(token: TokenLike | None) -> bool:
        if token is None:
            return False
        return bool(token.text) and all(char.isalnum() or ("가" <= char <= "힣") for char in token.text)

    if ctx is not None:
        token_start, token_end = _find_token_span(ctx, start, end)
        if token_start is not None and token_end is not None:
            prev_token = _get_prev_non_space_token(ctx, token_start)
            next_token = _get_next_non_space_token(ctx, token_end)
            if prev_token is not None and prev_token.end == start and _is_attached_word(prev_token):
                return deny("attached lexical token on the left")
            if next_token is not None and next_token.start == end and _is_attached_word(next_token):
                return deny("attached lexical token on the right")
            return allow("independent korean hour token boundary")

    if start > 0:
        prev_char = text[start - 1]
        if prev_char.isalnum() or ("가" <= prev_char <= "힣"):
            return deny("attached lexical character on the left")
    if end < len(text):
        next_char = text[end]
        if next_char.isalnum() or ("가" <= next_char <= "힣"):
            return deny("attached lexical character on the right")
    return allow("independent korean hour character boundary")
