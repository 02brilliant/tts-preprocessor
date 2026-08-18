from __future__ import annotations

_UNARY_SIGN_OPENERS = frozenset("([{'\"“‘")
_SAFE_TAIL_BOUNDARIES = frozenset(" \t\r\n.,!?;:)]}”’\"'")
CLOCK_HOUR_LEXICAL_WORDS = tuple(
    sorted(("시리즈", "시스템", "시장", "시험", "시즌"), key=len, reverse=True)
)
CONTEXTUAL_RESIDUAL_UNITS = tuple(
    sorted(
        (
            "가지",
            "분",
            "번",
            "점",
            "조",
            "대",
            "부",
            "동",
            "호",
            "판",
            "단",
            "등",
            "척",
            "장",
            "권",
            "편",
            "층",
            "명",
            "개",
        ),
        key=len,
        reverse=True,
    )
)
_RESIDUAL_NO_SPACE_TAILS = tuple(
    sorted(
        (
            "였습니다",
            "이었습니다",
            "이었고",
            "였지만",
            "였으며",
            "였고",
            "였다",
            "입니다",
            "이다",
            "이고",
            "으로",
            "에서",
            "에게",
            "부터",
            "까지",
            "처럼",
            "마다",
            "짜리",
            "정도",
            "간",
            "은",
            "는",
            "이",
            "가",
            "의",
            "을",
            "를",
            "에",
            "로",
            "와",
            "과",
            "도",
            "만",
            "씩",
            "쯤",
            "꼴",
            "당",
        ),
        key=len,
        reverse=True,
    )
)


def needs_residual_hangul_space(raw_text: str, index: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if index < 0 or index >= len(raw_text):
        return False
    if not ("\uac00" <= raw_text[index] <= "\ud7a3"):
        return False
    rest = raw_text[index:]
    return is_clock_hour_residual_tail(rest) or is_contextual_residual_unit_tail(rest)


def is_clock_hour_residual_tail(rest: str) -> bool:
    if not isinstance(rest, str):
        raise TypeError("rest must be str")
    for word in CLOCK_HOUR_LEXICAL_WORDS:
        if rest.startswith(word) and _residual_tail_boundary_ok(rest, len(word)):
            return True
    if rest.startswith("시간"):
        return False
    if not rest.startswith("시"):
        return False
    return _residual_tail_boundary_ok(rest, 1)


def is_contextual_residual_unit_tail(rest: str) -> bool:
    if not isinstance(rest, str):
        raise TypeError("rest must be str")
    for unit in CONTEXTUAL_RESIDUAL_UNITS:
        if rest.startswith(unit) and _residual_tail_boundary_ok(rest, len(unit)):
            return True
    return False


def valid_unary_sign_left_boundary(raw_text: str, start: int) -> bool:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if start <= 0:
        return True
    prev = raw_text[start - 1]
    return prev.isspace() or prev in _UNARY_SIGN_OPENERS


def _residual_tail_boundary_ok(rest: str, consumed: int) -> bool:
    pos = consumed
    while pos < len(rest):
        found = next(
            (tail for tail in _RESIDUAL_NO_SPACE_TAILS if rest.startswith(tail, pos)),
            None,
        )
        if found is None:
            break
        pos += len(found)
    return pos == len(rest) or rest[pos] in _SAFE_TAIL_BOUNDARIES
