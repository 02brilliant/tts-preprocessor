from __future__ import annotations

from .models import GateDecision, allow, deny


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
EMERGENCY_ALLOWED_TAILS = {
    "",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "에게",
    "로",
    "으로",
    "와",
    "과",
    "도",
    "만",
    "부터",
    "까지",
    "처럼",
}


def evaluate_emergency_context(
    *,
    candidate: str,
    text: str,
    number: str,
    tail: str,
    **_: object,
) -> GateDecision:
    del candidate
    if number not in {"112", "119"}:
        return deny("not an emergency candidate")
    if not any(keyword in text for keyword in EMERGENCY_CONTEXT_KEYWORDS):
        return deny("missing emergency context keyword")
    if tail not in EMERGENCY_ALLOWED_TAILS:
        return deny("tail is not on the emergency whitelist", tail=tail or "<empty>")
    return allow("emergency context and tail whitelist matched", tail=tail or "<empty>")
