from __future__ import annotations

from dataclasses import dataclass

from engine.parsers.numeric_date_parsers import read_integer_ko

from .models import GateDecision, allow, deny


@dataclass(frozen=True, slots=True)
class CounterPolicy:
    mode: str
    threshold: int | None = None
    attach_without_space: bool = False


COUNTER_POLICY_TABLE = {
    "사람": CounterPolicy("native_only"),
    "마리": CounterPolicy("native_only"),
    "그루": CounterPolicy("native_only"),
    "송이": CounterPolicy("native_only"),
    "자루": CounterPolicy("native_only"),
    "알": CounterPolicy("native_only"),
    "벌": CounterPolicy("native_only"),
    "켤레": CounterPolicy("native_only"),
    "그릇": CounterPolicy("native_only"),
    "공기": CounterPolicy("native_only"),
    "잔": CounterPolicy("native_only"),
    "병": CounterPolicy("native_only"),
    "조각": CounterPolicy("native_only"),
    "살": CounterPolicy("native_only"),
    "개": CounterPolicy("hybrid", threshold=30),
    "권": CounterPolicy("hybrid", threshold=30),
    "장": CounterPolicy("hybrid", threshold=30),
    "명": CounterPolicy("hybrid", threshold=30),
    "층": CounterPolicy("sino_only"),
    "호": CounterPolicy("sino_only"),
    "동": CounterPolicy("sino_only"),
    "년": CounterPolicy("sino_only", attach_without_space=True),
    "월": CounterPolicy("sino_only", attach_without_space=True),
    "일": CounterPolicy("sino_only", attach_without_space=True),
    "개월": CounterPolicy("sino_only", attach_without_space=True),
    "원": CounterPolicy("sino_only"),
    "도": CounterPolicy("sino_only", attach_without_space=True),
    "미터": CounterPolicy("sino_only"),
    "킬로그램": CounterPolicy("sino_only"),
    "학년": CounterPolicy("sino_only", attach_without_space=True),
    "학기": CounterPolicy("sino_only", attach_without_space=True),
    "회": CounterPolicy("sino_only", attach_without_space=True),
}
COUNTER_NOUNS = tuple(COUNTER_POLICY_TABLE)
COUNTER_NOUN_PATTERN = "|".join(sorted(COUNTER_NOUNS, key=len, reverse=True))
NATIVE_ONES = {
    1: "한",
    2: "두",
    3: "세",
    4: "네",
    5: "다섯",
    6: "여섯",
    7: "일곱",
    8: "여덟",
    9: "아홉",
}
NATIVE_TENS = {
    10: "열",
    20: "스물",
    30: "서른",
    40: "마흔",
    50: "쉰",
    60: "예순",
    70: "일흔",
    80: "여든",
    90: "아흔",
}
def resolve_counter_policy(counter: str) -> CounterPolicy | None:
    return COUNTER_POLICY_TABLE.get(counter)


def read_native_counter_number(value: int) -> str | None:
    if not 1 <= value <= 99:
        return None
    if value <= 9:
        return NATIVE_ONES[value]
    if value == 10:
        return NATIVE_TENS[10]
    if value < 20:
        return f"{NATIVE_TENS[10]}{NATIVE_ONES[value - 10]}"
    if value in NATIVE_TENS:
        return "스무" if value == 20 else NATIVE_TENS[value]
    tens = (value // 10) * 10
    ones = value % 10
    if tens not in NATIVE_TENS or ones not in NATIVE_ONES:
        return None
    return f"{NATIVE_TENS[tens]}{NATIVE_ONES[ones]}"


NATIVE_COUNTER_NUMBER_TO_VALUE = {
    reading: value
    for value in range(1, 100)
    if (reading := read_native_counter_number(value)) is not None
}


def should_apply_counter_policy(value: int, counter: str) -> bool:
    del value
    return counter in COUNTER_POLICY_TABLE


def read_counter_number_with_policy(value: int, counter: str) -> str | None:
    policy = resolve_counter_policy(counter)
    if policy is None:
        return None
    if policy.mode == "native_only":
        return read_native_counter_number(value) or read_integer_ko(str(value))
    if policy.mode == "sino_only":
        return read_integer_ko(str(value))
    if policy.mode == "hybrid":
        if policy.threshold is not None and value <= policy.threshold:
            native = read_native_counter_number(value)
            if native is not None:
                return native
        return read_integer_ko(str(value))
    return None


def format_counter_reading(reading: str, counter: str) -> str:
    policy = resolve_counter_policy(counter)
    if policy is not None and policy.attach_without_space:
        return f"{reading}{counter}"
    return f"{reading} {counter}"


def evaluate_counter_policy(
    *,
    candidate: str,
    number_text: str,
    counter: str,
    **_: object,
) -> GateDecision:
    del candidate
    policy = resolve_counter_policy(counter)
    if policy is None:
        return deny("counter noun is not in the policy table", counter=counter)
    if not number_text.isdigit():
        return deny("counter requires plain digit prefix", counter=counter)
    if number_text in {"112", "119"}:
        return deny("emergency numbers are excluded from counter override", counter=counter)
    value = int(number_text)
    if counter == "시간" and value > 24:
        return deny("hour-like counter exceeds allowed range", counter=counter)
    if counter in {"사람", "마리", "그루", "송이", "자루", "알", "벌", "켤레", "그릇", "공기", "잔", "병", "조각", "살"} and value > 99:
        return deny("native-only counter exceeds 1-99 range", counter=counter)
    mode = policy.mode
    if mode == "hybrid" and policy.threshold is not None and value > policy.threshold:
        return allow("hybrid counter falls back to sino mode", counter=counter, mode="sino_only")
    return allow("counter policy matched", counter=counter, mode=mode)
