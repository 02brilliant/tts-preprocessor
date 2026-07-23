from __future__ import annotations

import re

from .models import GateDecision, allow, deny


EVENT_KEYWORD_WHITELIST = (
    "비상계엄",
    "계엄",
    "사태",
    "혁명",
    "민주화 운동",
    "민주화운동",
    "전쟁",
    "항쟁",
    "운동",
    "사건",
    "정책",
    "대책",
    "사고",
    "기념일",
    "선거",
)
_NORMALIZED_EVENT_KEYWORDS = {re.sub(r"\s+", "", keyword) for keyword in EVENT_KEYWORD_WHITELIST}


def evaluate_event_keyword(
    *,
    left_text: str,
    right_text: str,
    keyword_text: str,
    **_: object,
) -> GateDecision:
    normalized_keyword = re.sub(r"\s+", "", keyword_text.strip())
    if normalized_keyword not in _NORMALIZED_EVENT_KEYWORDS:
        return deny("keyword is not on the event whitelist")

    if not (1 <= int(left_text) <= 12):
        return deny("left dotted block is outside event range")
    if not (1 <= int(right_text) <= 31):
        return deny("right dotted block is outside event range")
    if len(right_text) == 1:
        return deny("one-digit right dotted block must preserve")
    return allow("immediate event keyword adjacency matched", keyword=normalized_keyword)
