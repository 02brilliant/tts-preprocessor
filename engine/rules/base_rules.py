from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable

from engine.dictionary.base_dictionary import PHONE_DIGIT_KO
from engine.gates import COUNTER_NOUN_PATTERN, COUNTER_NOUNS, GATE_REGISTRY, gate_log_scope
from engine.gates.counter_gate import (
    format_counter_reading,
    read_counter_number_with_policy,
)
from engine.gates.generic_gate import classify_slash_context, looks_like_url_or_path
from engine.parsers.numeric_date_parsers import (
    NUMERIC_INTEGER_PATTERN,
    classify_numeric_pattern,
    normalize_number_text,
    read_decimal_ko,
    read_number_token_ko,
    read_integer_ko,
    read_negative_ko,
    read_number_ko,
    try_parse_comma_number_with_suffix,
    try_parse_date,
    try_parse_date_range,
    try_parse_fraction,
    try_parse_number_range,
    try_parse_time,
    try_parse_year_range,
)
from engine.parsers.special_parsers import (
    try_parse_angle,
    try_parse_ph,
    try_parse_phone,
    try_parse_upper_decimal_compound,
)
from engine.parsers.unit_currency_parsers import (
    try_parse_basic_unit,
    try_parse_compact_krw,
    try_parse_decimal_attached_unit,
    try_parse_duration,
    try_parse_eur,
    try_parse_filesize,
    try_parse_gbp,
    try_parse_jpy,
    try_parse_krw,
    try_parse_percent,
    try_parse_percent_point,
    try_parse_signed_degree_quantity,
    try_parse_temperature,
    try_parse_usd,
)
from engine.tokenizer.tokenizer import Token, tokenize


@dataclass
class RuleContext:
    original_text: str
    preprocessed_text: str
    tokenized_text: str
    tokens: list[Token]
    gate_logs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str
    parser: Callable[[str], str | None]
    allow_josa: bool = True
    gate_name: str | None = None


@dataclass(frozen=True)
class RuleGroup:
    name: str
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class RuleStage:
    name: str
    runner: Callable[[str, "RuleContext"], str]
    role: str
    owned_transforms: tuple[str, ...]
    precondition: Callable[[str, "RuleContext"], bool] | None = None


class RuleStageRole(StrEnum):
    STRUCTURED_PARSER = "structured_parser"


_ACTIVE_RULE_STAGE: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tts_preprocessor_active_rule_stage",
    default=None,
)


def _assert_rule_stage(stage_name: str) -> None:
    active_stage = _ACTIVE_RULE_STAGE.get()
    if active_stage != stage_name:
        raise AssertionError(f"{stage_name} must run from RULE_PIPELINE stage ownership")


_BOUNDARY_CLASS = r"A-Za-z0-9가-힣·"
_KOREAN_NUMBER_TOKEN_CORE = r"[영일이삼사오육칠팔구십백천만억조경쩜한두세네다섯여섯일곱여덟아홉열스물서른마흔쉰예순일흔여든아흔]+"
_JOSA_PATTERN = r"(?:으로|에서|에게|한테|이랑|까지|부터|이란|에는|은|는|이|가|을|를|와|과|의|에|로|만|도|란|뿐|고)"
_TRAILING_KO_PATTERN = rf"(?:이고|이며|이다|{_JOSA_PATTERN}|다)"
_PURE_TRAILING_KO_PATTERN = re.compile(rf"(?:{_TRAILING_KO_PATTERN})+")
_WHITESPACE_RE = re.compile(r"\s+")
_WHITESPACE_SEARCH_RE = re.compile(r"\s")
_MIDDLE_DOT_STRUCTURED_RE = re.compile(r"\d+(?:·\d+)+")
_TEMP_SYMBOL_RE = re.compile(r"(?P<number>-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?)(?P<unit>ºC|ºF|º씨|º에프|º)")
_RANGE_SEPARATOR_TRANSLATION = str.maketrans({"∼": "~", "～": "~"})
_PH_NUMBER_PROTECT_RE = re.compile(r"(?P<prefix>pH\s*)(?P<number>\d+(?:\.\d+)?)")
_VERSION_IP_PROTECT_RE = re.compile(r"\b(?P<number>\d{1,3}(?:\.\d{1,3}){2,})\b")
_PH_NUMBER_DIGIT_ENCODE = {"0": "A", "1": "B", "2": "C", "3": "D", "4": "E", "5": "F", "6": "G", "7": "H", "8": "I", "9": "J", ".": "P"}
_PH_NUMBER_DIGIT_DECODE = {value: key for key, value in _PH_NUMBER_DIGIT_ENCODE.items()}
_PH_NUMBER_PLACEHOLDER_RE = re.compile(r"__PHNUM__(?P<number>[A-JP]+)__")
_PLAIN_DECIMAL_CAPTURE_RE = re.compile(r"\d+\.(\d+)")
_NORMALIZED_DECIMAL_RE = re.compile(r"\d+\.\d+")
_NORMALIZED_INTEGER_RE = re.compile(r"\d+")
_HYPHEN_DIGIT_BLOCKS_RE = re.compile(r"^\d{1,8}(?:-\d{1,8}){2,8}$")
_SLASH_FRACTION_RE = re.compile(r"\d+/\d+")
_SLASH_DATE_RE = re.compile(r"\d{4}/\d{1,2}/\d{1,2}")
_SLASH_UNIT_RE = re.compile(r"[A-Za-z]{1,4}/[A-Za-z]{1,4}")
_SLASH_OR_RE = re.compile(r"[^/\d\s]+/[^/\d\s]+")
_TIME_VALUE_RE = re.compile(r"\d{1,2}:\d{1,2}")
_NUMERIC_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)?\s*")
_KOREAN_COUNTER_SPACING_RE = re.compile(
    r"(일|이|삼|사|오|육|칠|팔|구|십|이십|삼십|사십|오십|육십|칠십|팔십|구십|백|천)(쪽)\b"
)
_EMERGENCY_NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9가-힣-])"
    r"(?P<number>112|119)"
    r"(?P<tail>[가-힣]+)?"
    r"(?=$|[\s,.!?]|[^A-Za-z0-9가-힣])"
)

_NATIVE_ONES = {
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
_NATIVE_TENS = {
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


def _preprocess(text: str) -> str:
    from engine.pipeline.transform_engine import normalize_comma_numbers

    current = normalize_comma_numbers(text)
    current = current.translate(_RANGE_SEPARATOR_TRANSLATION)
    current = _normalize_temperature_symbols(current)
    current = _protect_event_dot_expressions(current)
    return current


def _normalize_temperature_symbols(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        tail = text[match.end() :]
        suffix_match = _PURE_TRAILING_KO_PATTERN.match(tail)
        if suffix_match is None and tail[:1] and re.match(rf"[{_BOUNDARY_CLASS}]", tail[0]):
            return match.group(0)
        if suffix_match is not None:
            suffix_end = suffix_match.end()
            if suffix_end < len(tail) and re.match(rf"[{_BOUNDARY_CLASS}]", tail[suffix_end]):
                return match.group(0)
        unit = match.group("unit")
        normalized_unit = "℉" if unit in {"ºF", "º에프"} else "℃"
        return f"{match.group('number')}{normalized_unit}"

    return _TEMP_SYMBOL_RE.sub(_replace, text)


def _protect_ph_number_literals(text: str) -> str:
    return _PH_NUMBER_PROTECT_RE.sub(
        lambda match: (
            f"{match.group('prefix')}__PHNUM__"
            f"{''.join(_PH_NUMBER_DIGIT_ENCODE[ch] for ch in match.group('number'))}__"
        ),
        text,
    )


def _restore_ph_number_literals(text: str) -> str:
    return _PH_NUMBER_PLACEHOLDER_RE.sub(
        lambda match: "".join(_PH_NUMBER_DIGIT_DECODE[ch] for ch in match.group("number")),
        text,
    )


def _build_rule_pattern(core: str, *, allow_josa: bool = True) -> str:
    if allow_josa:
        right = rf"(?=(?:{_TRAILING_KO_PATTERN})(?![{_BOUNDARY_CLASS}])|$|[^{_BOUNDARY_CLASS}])"
    else:
        right = rf"(?=$|[^{_BOUNDARY_CLASS}])"
    return rf"(?<![{_BOUNDARY_CLASS}])(?:{core}){right}"


def _apply_pattern(text: str, pattern: str, replacer) -> str:
    regex = re.compile(pattern)

    def _replace(match: re.Match[str]) -> str:
        original = match.group(0)
        replaced = replacer(original)
        if replaced is None:
            return original
        return replaced

    return regex.sub(_replace, text)


def apply_rule(text: str, rule: Rule, ctx: RuleContext | None = None) -> str:
    pattern = _build_rule_pattern(rule.pattern, allow_josa=rule.allow_josa)

    def replacer(match):
        candidate = match.group(0)
        if rule.gate_name is not None:
            decision = GATE_REGISTRY.evaluate(
                rule.gate_name,
                gate_logs=ctx.gate_logs if ctx is not None else None,
                candidate=candidate,
                text=text,
                start=match.start(),
                end=match.end(),
                ctx=ctx,
                rule=rule,
            )
            if not decision.allowed:
                return candidate
        parsed = rule.parser(candidate)
        return parsed if parsed is not None else candidate

    return re.sub(pattern, replacer, text)


def apply_rule_group(text: str, group: RuleGroup, ctx: RuleContext | None = None) -> str:
    current = text
    for rule in group.rules:
        current = apply_rule(current, rule, ctx)
    return current


_LIKELY_SCORE_CONTEXT_PATTERN = re.compile(
    r"(?:스코어|score|전반|후반|연장|득점|승부차기|세트|게임|라운드|ratio|port|vs\.?|VS\.?)"
)
_TIME_PREFIX_CONTEXT_TOKENS = ("오전", "오후", "새벽", "아침", "정오", "밤", "저녁")
_TIME_EVENT_CONTEXT_TOKENS = (
    "출발", "도착", "시작", "종료", "마감", "개시", "오픈", "폐장",
    "예약", "탑승", "발차", "상영", "회의", "수업", "진료", "시각", "시간",
)
_TIME_POSTPOSITION_TOKENS = ("에", "까지", "부터", "경", "쯤", "정각")
_TIME_COLON_PATTERN = re.compile(
    r"(?:(?:오전|오후|새벽|아침|정오|밤|저녁)\s*)?\d{1,2}:\d{2}(?::\d{2})?"
)
_KOREAN_DATE_CONTEXT_RE = re.compile(
    rf"(?:{_KOREAN_NUMBER_TOKEN_CORE}년\s*{_KOREAN_NUMBER_TOKEN_CORE}월\s*{_KOREAN_NUMBER_TOKEN_CORE}일|{_KOREAN_NUMBER_TOKEN_CORE}월\s*{_KOREAN_NUMBER_TOKEN_CORE}일)$"
)
_DURATION_UNIT_SUFFIX_CORE = r"(?:시간|분|초|일|개월|년)"
_BASIC_UNIT_SUFFIX_CORE = r"(?:GB/s|km/h|㎞/h|km/L|km/l|km/ℓ|㎞/L|㎞/l|㎞/ℓ|m/L|m/l|m/ℓ|m/s|km/s|㎞/s|kWh|Wh|MWh|kW|MW|MHz|GHz|mL|kg|km|cm|mm|mg|㎡|m²|㎥|m³|g|m|L|W|도)"
_FILESIZE_UNIT_SUFFIX_CORE = r"(?:KB|MB|GB|TB)"
_UNIT_PARTICLE_SUFFIX_CORE = r"(?:입니다|합니까|하고|하며|하면서|으로|에서|에게|한테|이랑|까지|부터|이란|에는|당|은|는|이|가|을|를|와|과|의|에|로|만|도|란|뿐|고|다)?"
# Compound units are the highest-priority unit pass because slash forms can
# otherwise collide with generic fraction/date/path handling.
COMPOUND_UNIT_MAP = {
    "km/h": "킬로미터 퍼 아워",
    "㎞/h": "킬로미터 퍼 아워",
    "m/s": "미터 퍼 세크",
    "km/L": "킬로미터 퍼 리터",
    "km/l": "킬로미터 퍼 리터",
    "km/ℓ": "킬로미터 퍼 리터",
    "㎞/L": "킬로미터 퍼 리터",
    "㎞/l": "킬로미터 퍼 리터",
    "㎞/ℓ": "킬로미터 퍼 리터",
    "m/L": "미터 퍼 리터",
    "m/l": "미터 퍼 리터",
    "m/ℓ": "미터 퍼 리터",
    "km/s": "킬로미터 퍼 세크",
    "㎞/s": "킬로미터 퍼 세크",
    "m/min": "미터 퍼 분",
    "kg/m3": "킬로그램 퍼 세제곱미터",
    "mg/dL": "밀리그램 퍼 데시리터",
    "kWh": "킬로와트시",
    "㎾h": "킬로와트시",
    "bps": "비피에스",
    "Mbps": "메가비피에스",
    "MB/s": "메가바이트 퍼 세크",
    "rpm": "알피엠",
    "㏘": "알피엠",
    "fps": "에프피에스",
    "ppm": "피피엠",
    "dBi": "디비아이",
}
# Special symbol units stay narrow and exact: standalone symbols may convert,
# and number+symbol uses the existing number reader.
SPECIAL_UNIT_MAP = {
    "㎜": "밀리미터",
    "㎝": "센티미터",
    "㎙": "미터",
    "㎞": "킬로미터",
    "㎎": "밀리그램",
    "㎏": "킬로그램",
    "㎖": "밀리리터",
    "ℓ": "리터",
    "㎐": "헤르츠",
    "㏈": "데시벨",
    "㎡": "제곱미터",
    "㎥": "세제곱미터",
    "%": "퍼센트",
    "％": "퍼센트",
    "‰": "퍼밀",
    "°": "도",
}
# Simple units are stricter: they only convert with a numeric prefix and keep
# safe trailing boundaries. Frequency units normalize only in numeric+unit
# contexts with those same guards.
SIMPLE_UNIT_MAP = {
    "mm": "밀리미터",
    "cm": "센티미터",
    "m": "미터",
    "km": "킬로미터",
    "mg": "밀리그램",
    "g": "그램",
    "kg": "킬로그램",
    "t": "톤",
    "mL": "밀리리터",
    "L": "리터",
    "V": "볼트",
    "A": "암페어",
    "W": "와트",
    "kW": "킬로와트",
    "MW": "메가와트",
    "Wh": "와트시",
    "kWh": "킬로와트시",
    "MWh": "메가와트시",
    "Hz": "헤르츠",
    "hz": "헤르츠",
    "dB": "데시벨",
    "bit": "비트",
    "Byte": "바이트",
    "KB": "킬로바이트",
    "MB": "메가바이트",
    "GB": "기가바이트",
    "TB": "테라바이트",
    "PB": "페타바이트",
    "kHz": "킬로헤르츠",
    "khz": "킬로헤르츠",
    "MHz": "메가헤르츠",
    "mhz": "메가헤르츠",
    "GHz": "기가헤르츠",
    "Ghz": "기가헤르츠",
    "ghz": "기가헤르츠",
    "Gbps": "기가비피에스",
    "Tbps": "테라비피에스",
    "도": "도",
}
# Semantic-layer registries stay whitelisted and exact-pattern based until a
# later live integration step wires them into the pipeline.
SEMANTIC_SPEED_UNIT_MAP = {
    "km/h": "킬로미터",
    "㎞/h": "킬로미터",
    "km/L": "킬로미터",
    "km/l": "킬로미터",
    "km/ℓ": "킬로미터",
    "㎞/L": "킬로미터",
    "㎞/l": "킬로미터",
    "㎞/ℓ": "킬로미터",
    "m/L": "미터",
    "m/l": "미터",
    "m/ℓ": "미터",
    "km/s": "킬로미터",
    "㎞/s": "킬로미터",
}
_CORE_SPEED_READING_MAP = {
    "km/h": ("시속", "킬로미터"),
    "㎞/h": ("시속", "킬로미터"),
    "km/L": ("리터당", "킬로미터"),
    "km/l": ("리터당", "킬로미터"),
    "km/ℓ": ("리터당", "킬로미터"),
    "㎞/L": ("리터당", "킬로미터"),
    "㎞/l": ("리터당", "킬로미터"),
    "㎞/ℓ": ("리터당", "킬로미터"),
    "m/L": ("리터당", "미터"),
    "m/l": ("리터당", "미터"),
    "m/ℓ": ("리터당", "미터"),
    "m/s": ("초속", "미터"),
    "km/s": ("초속", "킬로미터"),
    "㎞/s": ("초속", "킬로미터"),
    "m/min": ("분속", "미터"),
}
SEMANTIC_CURRENCY_PREFIX_MAP = {
    "USD": "달러",
    "KRW": "원",
    "EUR": "유로",
    "JPY": "엔",
    "GBP": "파운드",
}
SEMANTIC_PREFIX_TERM_MAP = {
    "pH": "피에이치",
    "Mach": "마하",
    "log": "로그",
}
SEMANTIC_BPS_FAMILY_MAP = {
    "Gbps": "기가비피에스",
    "Tbps": "테라비피에스",
}
SEMANTIC_TILDE_COUNTER_SUFFIXES = ("쪽",)
_LIVE_SIMPLE_UNIT_SKIP = {"t", "A", "V"}
_EMERGENCY_NUMBER_TRIGGERS = ("112", "119")
_EMERGENCY_CONTEXT_KEYWORDS = (
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
_EMERGENCY_ALLOWED_TAILS = {
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
_COUNTER_NOUN_TRIGGERS = COUNTER_NOUNS
_TIME_TRIGGER_TOKENS = ("오전", "오후", "새벽", "아침", "정오", "밤", "저녁", "시", "시간", "시각", "출발", "도착", "시작", "종료", "탑승", ":")
_DATE_TRIGGER_TOKENS = ("년", "월", "일", ".", "/", "-")
_PERCENT_TEMPERATURE_CURRENCY_TRIGGERS = ("%", "원", "$", "€", "¥", "￥", "£", "₩", "℃", "℉", "º", "도")
_COMPOUND_UNIT_TRIGGERS = tuple(COMPOUND_UNIT_MAP)
_CORE_SPEED_TRIGGERS = ("km/h", "㎞/h", "km/L", "km/l", "km/ℓ", "㎞/L", "㎞/l", "㎞/ℓ", "m/L", "m/l", "m/ℓ", "m/s", "km/s", "㎞/s", "m/min")
_SPECIAL_UNIT_TRIGGERS = tuple(SPECIAL_UNIT_MAP)
_SIMPLE_UNIT_TRIGGERS = tuple(unit for unit in SIMPLE_UNIT_MAP if unit not in _LIVE_SIMPLE_UNIT_SKIP)
_DURATION_UNIT_TRIGGERS = ("시간", "분", "초", "일", "개월", "년")
_FILESIZE_UNIT_TRIGGERS = ("KB", "MB", "GB", "TB")
_SPECIAL_RULE_TRIGGERS = ("-", ".", "pH", "°")
_UNIT_MARKERS = tuple(
    sorted(
        {
            *COMPOUND_UNIT_MAP.keys(),
            *SPECIAL_UNIT_MAP.keys(),
            *SIMPLE_UNIT_MAP.keys(),
        },
        key=len,
        reverse=True,
    )
)
SLASH_CONTEXT_DATE = "date"
SLASH_CONTEXT_FRACTION = "fraction"
SLASH_CONTEXT_UNIT = "unit"
SLASH_CONTEXT_OR = "or"
SLASH_CONTEXT_UNKNOWN = "unknown"
SLASH_CONTEXT_URL = "url"
_EVENT_DOT_KEYWORD_SPECS = (
    (r"비상계엄", "MARTIAL_LAW", "비상계엄"),
    (r"민주화\s*운동", "DEMOCRACY_MOVEMENT", "민주화 운동"),
    (r"계엄", "MARTIAL", "계엄"),
    (r"사태", "CRISIS", "사태"),
    (r"혁명", "REVOLUTION", "혁명"),
    (r"민주화", "DEMOCRACY", "민주화"),
    (r"전쟁", "WAR", "전쟁"),
    (r"항쟁", "UPRISING", "항쟁"),
    (r"운동", "MOVEMENT", "운동"),
    (r"사건", "INCIDENT", "사건"),
    (r"정책", "POLICY", "정책"),
    (r"대책", "COUNTERMEASURE", "대책"),
    (r"사고", "ACCIDENT", "사고"),
    (r"기념일", "ANNIVERSARY", "기념일"),
    (r"선거", "ELECTION", "선거"),
)
_EVENT_DOT_KEYWORD_PATTERN = "|".join(pattern for pattern, _, _ in _EVENT_DOT_KEYWORD_SPECS)
_EVENT_DOT_KEYWORD_BY_NORMALIZED = {
    _WHITESPACE_RE.sub("", spoken): (slug, spoken)
    for _, slug, spoken in _EVENT_DOT_KEYWORD_SPECS
}
_EVENT_DOT_SUFFIXES = tuple(spoken for _, _, spoken in _EVENT_DOT_KEYWORD_SPECS)
_EVENT_DOT_PLACEHOLDER_DIGITS = {
    "0": "A",
    "1": "B",
    "2": "C",
    "3": "D",
    "4": "E",
    "5": "F",
    "6": "G",
    "7": "H",
    "8": "I",
    "9": "J",
}
_EVENT_DOT_DECODE_DIGITS = {value: key for key, value in _EVENT_DOT_PLACEHOLDER_DIGITS.items()}
_EVENT_DOT_PLACEHOLDER_PATTERN = re.compile(
    r"__EVENT_DOT__(?P<left>[A-J]{1,2})__(?P<right>[A-J]{1,2})__(?P<slug>[A-Z_]+)__"
)
_URL_PLACEHOLDER_PATTERN = re.compile(r"__URL_PROTECT__(?P<index>[A-Z]+)__")
_EVENT_DOT_SPOKEN_BY_SLUG = {
    slug: spoken for _, slug, spoken in _EVENT_DOT_KEYWORD_SPECS
}
def _read_native_counter_number(value: int) -> str | None:
    if not 1 <= value <= 99:
        return None

    if value <= 9:
        return _NATIVE_ONES[value]
    if value == 10:
        return _NATIVE_TENS[10]
    if value < 20:
        return f"{_NATIVE_TENS[10]}{_NATIVE_ONES[value - 10]}"
    if value in _NATIVE_TENS:
        return "스무" if value == 20 else _NATIVE_TENS[value]

    tens = (value // 10) * 10
    ones = value % 10
    if tens not in _NATIVE_TENS or ones not in _NATIVE_ONES:
        return None
    return f"{_NATIVE_TENS[tens]}{_NATIVE_ONES[ones]}"


def _apply_emergency_number_rules(text: str) -> str:
    _assert_rule_stage("emergency")
    if not any(trigger in text for trigger in _EMERGENCY_NUMBER_TRIGGERS):
        return text

    readings = {"112": "일일이", "119": "일일구"}

    def _replace(match: re.Match[str]) -> str:
        number = match.group("number")
        tail = match.group("tail") or ""
        decision = GATE_REGISTRY.evaluate(
            "emergency_context",
            candidate=match.group(0),
            text=text,
            start=match.start(),
            end=match.end(),
            number=number,
            tail=tail,
        )
        if decision.allowed:
            return f"{readings[number]}{tail}"
        return f"{read_integer_ko(number)}{tail}"

    return _EMERGENCY_NUMBER_PATTERN.sub(_replace, text)


def _try_parse_counter_noun(text: str) -> str | None:
    match = re.fullmatch(rf"(\d{{1,2}})(?:\s*)({COUNTER_NOUN_PATTERN})", text)
    if not match:
        return None

    number_text, unit_text = match.groups()
    decision = GATE_REGISTRY.evaluate(
        "counter_policy",
        candidate=text,
        number_text=number_text,
        counter=unit_text,
    )
    if not decision.allowed:
        return None
    reading = read_counter_number_with_policy(int(number_text), unit_text)
    if reading is None:
        return None

    return format_counter_reading(reading, unit_text)


def _apply_counter_noun_rules(text: str) -> str:
    _assert_rule_stage("counter_noun")
    if not any(trigger in text for trigger in _COUNTER_NOUN_TRIGGERS):
        return text

    return _apply_pattern(
        text,
        _build_rule_pattern(rf"\d{{1,2}}\s*(?:{COUNTER_NOUN_PATTERN})"),
        _try_parse_counter_noun,
    )


def _looks_like_ambiguous_decimal(text: str) -> bool:
    if text.count(".") != 1:
        return True

    integer_part, decimal_part = text.split(".")

    if (
        len(integer_part) == 4
        and len(decimal_part) <= 2
        and integer_part.startswith(("19", "20"))
    ):
        return True

    # Standard decimals with contiguous digits on both sides normalize unless
    # the event-number whitelist matched earlier; keep only the leading-zero
    # integer guard here.
    if len(integer_part) == 2 and integer_part.startswith("0"):
        return True

    return False


def _has_supported_fractional_length(text: str) -> bool:
    match = _PLAIN_DECIMAL_CAPTURE_RE.fullmatch(text)
    if not match:
        return False
    return 1 <= len(match.group(1)) <= 6


def _classify_slash_context(text: str) -> str:
    return classify_slash_context(text)


def _try_parse_date_by_slash_context(text: str) -> str | None:
    if "/" in text:
        decision = GATE_REGISTRY.evaluate("slash_date_context", candidate=text)
        if not decision.allowed:
            return None
    return try_parse_date(text)


def _try_parse_fraction_by_slash_context(text: str) -> str | None:
    if "/" in text:
        decision = GATE_REGISTRY.evaluate("slash_fraction_context", candidate=text)
        if not decision.allowed:
            return None
    return try_parse_fraction(text)


def _try_parse_decimal(text: str) -> str | None:
    kind = classify_numeric_pattern(text)
    if kind not in {"comma_decimal", "plain_decimal"}:
        return None

    normalized = normalize_number_text(text)
    if normalized is None or not _NORMALIZED_DECIMAL_RE.fullmatch(normalized):
        return None
    if not _has_supported_fractional_length(normalized):
        return None
    left, right = normalized.split(".", 1)
    # Conservative guard for short repeated dotted forms such as 12.12 that
    # are commonly event-style or commemorative markers outside explicit event context.
    if len(left) == len(right) == 2 and left == right:
        return None
    if kind == "plain_decimal" and _looks_like_ambiguous_decimal(normalized):
        return None
    return read_decimal_ko(normalized)


def _is_middle_dot_date_like_blocks(left_text: str, right_text: str) -> bool:
    if (len(left_text) > 1 and left_text.startswith("0")) or (
        len(right_text) > 1 and right_text.startswith("0")
    ):
        return False
    left_value = int(left_text)
    right_value = int(right_text)
    return 1 <= left_value <= 12 and 1 <= right_value <= 31


def try_parse_middle_dot_structured(text: str) -> str | None:
    if _WHITESPACE_SEARCH_RE.search(text):
        return None
    if _MIDDLE_DOT_STRUCTURED_RE.fullmatch(text) is None:
        return None

    blocks = text.split("·")
    if len(blocks) == 2 and _is_middle_dot_date_like_blocks(blocks[0], blocks[1]):
        left_reading = read_number_token_ko(
            blocks[0],
            {"category": "middle_dot_structured", "preferred_mode": "NUMBER_MODE"},
        )
        right_reading = read_number_token_ko(
            blocks[1],
            {"category": "middle_dot_structured", "preferred_mode": "DIGIT_MODE"},
        )
        if left_reading is None or right_reading is None:
            return None
        return f"{left_reading} {right_reading}"

    block_readings: list[str] = []
    for block in blocks:
        block_reading = read_number_token_ko(
            block,
            {"category": "middle_dot_structured", "preferred_mode": "DIGIT_MODE"},
        )
        if block_reading is None:
            return None
        block_readings.append(block_reading)
    return " ".join(block_readings)


def _read_event_dot_expression(left_text: str, right_text: str) -> str:
    left_reading = read_integer_ko(left_text)
    if left_text == "12" and right_text == "12":
        right_reading = read_integer_ko(right_text)
    elif len(right_text) == 1:
        right_reading = read_integer_ko(right_text)
    else:
        right_reading = "".join(PHONE_DIGIT_KO[digit] for digit in right_text)
    return f"{left_reading}{right_reading}"


def _encode_event_dot_part(text: str) -> str:
    return "".join(_EVENT_DOT_PLACEHOLDER_DIGITS[digit] for digit in text)


def _decode_event_dot_part(text: str) -> str:
    return "".join(_EVENT_DOT_DECODE_DIGITS[char] for char in text)


def _is_valid_event_dot_numbers(left_text: str, right_text: str) -> bool:
    left_value = int(left_text)
    right_value = int(right_text)
    return 1 <= left_value <= 12 and 1 <= right_value <= 31


def _is_event_dot_keyword(keyword_text: str) -> bool:
    normalized = _WHITESPACE_RE.sub("", keyword_text)
    return any(normalized.endswith(_WHITESPACE_RE.sub("", suffix)) for suffix in _EVENT_DOT_SUFFIXES)


def _protect_event_dot_expressions(text: str) -> str:
    # Event-dot is intentionally whitelist-based: only an immediate keyword
    # match after N.N enters the protect -> restore path.
    # Do not broaden this to sentence-level semantic inference such as
    # "the same sentence later contains 계엄".
    regex = re.compile(
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<left>\d{{1,2}})\.(?P<right>\d{{1,2}})"
        rf"(?P<space>\s*)"
        rf"(?P<keyword>(?:민주화\s*운동|[가-힣]*(?:비상계엄|계엄|사태|혁명|민주화|전쟁|항쟁|운동|사건|정책|대책|사고|기념일|선거)))"
        rf"(?=(?:{_TRAILING_KO_PATTERN})(?![{_BOUNDARY_CLASS}])|$|[^{_BOUNDARY_CLASS}])"
    )

    def _replace(match: re.Match[str]) -> str:
        left_text = match.group("left")
        right_text = match.group("right")
        keyword_text = _WHITESPACE_RE.sub(" ", match.group("keyword").strip())
        decision = GATE_REGISTRY.evaluate(
            "event_keyword",
            candidate=match.group(0),
            text=text,
            start=match.start(),
            end=match.end(),
            left_text=left_text,
            right_text=right_text,
            keyword_text=keyword_text,
        )
        if not decision.allowed:
            return match.group(0)
        return f"{_read_event_dot_expression(left_text, right_text)} {keyword_text}"

    return regex.sub(_replace, text)


def _restore_event_dot_expressions(text: str) -> str:
    # Restore only placeholders produced by the whitelist-based protector
    # above so event-style reading stays exact and local to the match.
    def _replace(match: re.Match[str]) -> str:
        keyword_text = _EVENT_DOT_SPOKEN_BY_SLUG.get(match.group("slug"))
        if keyword_text is None:
            return match.group(0)

        left_text = _decode_event_dot_part(match.group("left"))
        right_text = _decode_event_dot_part(match.group("right"))
        return f"{_read_event_dot_expression(left_text, right_text)} {keyword_text}"

    return _EVENT_DOT_PLACEHOLDER_PATTERN.sub(_replace, text)


def _encode_url_index(value: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    value += 1
    chars: list[str] = []
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        chars.append(alphabet[remainder])
    return "".join(reversed(chars))


def _protect_urls(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    pattern = re.compile(r"https?://[^\s]+")

    def _replace(match: re.Match[str]) -> str:
        key = f"__URL_PROTECT__{_encode_url_index(len(replacements))}__"
        replacements[key] = match.group(0)
        return key

    return pattern.sub(_replace, text), replacements


def _restore_urls(text: str, replacements: dict[str, str]) -> str:
    if not replacements:
        return text

    def _replace(match: re.Match[str]) -> str:
        return replacements.get(match.group(0), match.group(0))

    return _URL_PLACEHOLDER_PATTERN.sub(_replace, text)


def find_token_span(ctx: RuleContext, start: int, end: int) -> tuple[int | None, int | None]:
    token_start = None
    token_end = None

    for i, token in enumerate(ctx.tokens):
        if token_start is None and token.start <= start < token.end:
            token_start = i
        if token.start < end <= token.end:
            token_end = i
            break

    return token_start, token_end


def get_prev_non_space_token(ctx: RuleContext, token_index: int):
    i = token_index - 1
    while i >= 0:
        token = ctx.tokens[i]
        if not token.text.isspace():
            return token
        i -= 1
    return None


def get_next_non_space_token(ctx: RuleContext, token_index: int):
    i = token_index + 1
    while i < len(ctx.tokens):
        token = ctx.tokens[i]
        if not token.text.isspace():
            return token
        i += 1
    return None


def _apply_plain_12_3_decimal_rules(text: str) -> str:
    if "12.3" not in text:
        return text

    regex = re.compile(_build_rule_pattern(r"12\.3", allow_josa=False))

    def _replace(match: re.Match[str]) -> str:
        original = match.group(0)
        decision = GATE_REGISTRY.evaluate(
            "decimal_context",
            candidate=original,
            text=text,
            start=match.start(),
            end=match.end(),
            ctx=None,
        )
        if not decision.allowed:
            return original
        replaced = _try_parse_decimal(original)
        if replaced is None:
            return original
        return replaced

    return regex.sub(_replace, text)


def is_valid_time_context(
    match: re.Match[str],
    text: str,
    ctx: RuleContext | None,
    rule: Rule,
) -> bool:
    value = match.group(0)
    if try_parse_time(value) is None:
        return False

    # H:MM:SS / HH:MM:SS is an independent clock pattern. Only HH:MM needs
    # the stronger ambiguity gate below.
    if value.count(":") == 2:
        return True

    start, end = match.span()
    if _TIME_VALUE_RE.fullmatch(value) and _TIME_COLON_PATTERN.fullmatch(text.strip()) and text.strip() == value:
        return False

    if len(_TIME_COLON_PATTERN.findall(text)) > 1:
        return False

    window_start = max(0, start - 16)
    window_end = min(len(text), end + 16)
    context_window = text[window_start:window_end]
    if _LIKELY_SCORE_CONTEXT_PATTERN.search(context_window):
        return False

    left_context = text[:start].rstrip()
    right_context = text[end:].lstrip()

    if any(left_context.endswith(prefix) for prefix in _TIME_PREFIX_CONTEXT_TOKENS):
        return True
    if any(right_context.startswith(postfix) for postfix in _TIME_POSTPOSITION_TOKENS):
        return True
    if any(token in left_context[-12:] for token in _TIME_EVENT_CONTEXT_TOKENS):
        return True
    if any(token in right_context[:12] for token in _TIME_EVENT_CONTEXT_TOKENS):
        return True
    if _KOREAN_DATE_CONTEXT_RE.search(left_context):
        return True

    if ctx is not None:
        token_start, token_end = find_token_span(ctx, start, end)
        if token_start is not None and token_end is not None:
            prev_token = get_prev_non_space_token(ctx, token_start)
            next_token = get_next_non_space_token(ctx, token_end)
            if prev_token is not None and prev_token.text in _TIME_PREFIX_CONTEXT_TOKENS:
                return True
            if next_token is not None and next_token.text in _TIME_POSTPOSITION_TOKENS:
                return True
            if prev_token is not None and any(token in prev_token.text for token in _TIME_EVENT_CONTEXT_TOKENS):
                return True
            if next_token is not None and any(token in next_token.text for token in _TIME_EVENT_CONTEXT_TOKENS):
                return True

    return False


def is_valid_hour_korean_context(
    match: re.Match[str],
    text: str,
    ctx: RuleContext | None,
    rule: Rule,
) -> bool:
    def _is_attached_word(token: Token | None) -> bool:
        if token is None:
            return False
        return bool(token.text) and all(char.isalnum() or ("가" <= char <= "힣") for char in token.text)

    start, end = match.span()
    if ctx is not None:
        token_start, token_end = find_token_span(ctx, start, end)
        if token_start is not None and token_end is not None:
            prev_token = get_prev_non_space_token(ctx, token_start)
            next_token = get_next_non_space_token(ctx, token_end)

            if prev_token is not None and prev_token.end == start and _is_attached_word(prev_token):
                return False
            if next_token is not None and next_token.start == end and _is_attached_word(next_token):
                return False
            return True

    if start > 0:
        prev_char = text[start - 1]
        if prev_char.isalnum() or ("가" <= prev_char <= "힣"):
            return False

    if end < len(text):
        next_char = text[end]
        if next_char.isalnum() or ("가" <= next_char <= "힣"):
            return False

    return True


def is_valid_decimal_context(
    match: re.Match[str],
    text: str,
    ctx: RuleContext | None,
    rule: Rule,
) -> bool:
    candidate = match.group(0)
    left, right = candidate.split(".", 1)
    if ctx is None:
        return True

    # Protect technical strings like IP addresses (multiple dots)
    start, end = match.span()
    if start > 0 and text[start-1] in (".", "#", "£", "$", "€", "₩", "￦", "¥", "￥"):
        return False
    if end < len(text) and text[end] == ".":
        return False
    
    # Protect version numbers (e.g., v1.2)
    if start > 0 and text[start-1].lower() == "v":
        return False

    # Protect alpha-numeric attached codes (e.g., Model3.1)
    if start > 0 and text[start-1].isalpha():
        return False
    if end < len(text) and text[end].isalpha():
        return False

    # Protect numbers within paths or URLs
    # find the surrounding word-like block
    word_start = start
    while word_start > 0 and not text[word_start-1].isspace():
        word_start -= 1
    word_end = end
    while word_end < len(text) and not text[word_end].isspace():
        word_end += 1
    
    surrounding_word = text[word_start:word_end]
    if _looks_like_url_or_path(surrounding_word):
        return False

    token_start, token_end = find_token_span(ctx, start, end)
    if token_start is None or token_end is None:
        return True

    return True


def is_valid_unit_context(
    match: re.Match[str],
    text: str,
    ctx: RuleContext | None,
    rule: Rule,
) -> bool:
    def _is_ascii_alnum(char: str) -> bool:
        return char.isascii() and char.isalnum()

    def _has_trailing_slash_alpha(start_index: int) -> bool:
        return (
            start_index + 1 < len(text)
            and text[start_index] == "/"
            and text[start_index + 1].isascii()
            and text[start_index + 1].isalpha()
        )

    start, end = match.span()
    if ctx is None:
        if end < len(text) and _has_trailing_slash_alpha(end):
            return False
        if end < len(text) and _is_ascii_alnum(text[end]):
            return False
        return True

    token_start, token_end = find_token_span(ctx, start, end)
    if token_start is None or token_end is None:
        if end < len(text) and _has_trailing_slash_alpha(end):
            return False
        if end < len(text) and _is_ascii_alnum(text[end]):
            return False
        return True

    if end < len(text) and _has_trailing_slash_alpha(end):
        return False

    next_token = get_next_non_space_token(ctx, token_end)
    if next_token is None:
        return True
    if next_token.start == end and next_token.text and _is_ascii_alnum(next_token.text[0]):
        return False
    return True


def is_exact_text_context(
    match: re.Match[str],
    text: str,
    ctx: RuleContext | None,
    rule: Rule,
) -> bool:
    return match.start() == 0 and match.end() == len(text)


def has_no_preceding_ascii_alpha(
    match: re.Match[str],
    text: str,
    ctx: RuleContext | None,
    rule: Rule,
) -> bool:
    index = match.start() - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    if index < 0:
        return True
    return not (text[index].isascii() and text[index].isalpha())


def _has_unit_markers(text: str) -> bool:
    return any(marker in text for marker in _UNIT_MARKERS)


def _is_safe_unit_context(text: str, match_span: tuple[int, int]) -> bool:
    start, end = match_span
    if start < 0 or end < start or end > len(text):
        return False
    return True


def _looks_like_url_or_path(text: str) -> bool:
    return looks_like_url_or_path(text)


def _has_numeric_prefix(token_text: str) -> bool:
    return _NUMERIC_PREFIX_RE.match(token_text) is not None


# Global safety filters stay intentionally conservative. Registered exact
# matches win, but risky or URL/path-like contexts are left unchanged.
def _is_safe_special_unit_token(token_text: str) -> bool:
    stripped = token_text.strip()
    if not stripped or _looks_like_url_or_path(stripped):
        return False

    for unit_text in sorted(SPECIAL_UNIT_MAP, key=len, reverse=True):
        if stripped == unit_text:
            return True
        if stripped.endswith(unit_text):
            prefix = stripped[: -len(unit_text)]
            if _NUMERIC_PREFIX_RE.fullmatch(prefix):
                return True
    return False


def _is_safe_compound_unit_token(token_text: str) -> bool:
    stripped = token_text.strip()
    if not stripped or _looks_like_url_or_path(stripped):
        return False

    for unit_text in sorted(COMPOUND_UNIT_MAP, key=len, reverse=True):
        if stripped == unit_text:
            return True
        if stripped.endswith(unit_text):
            prefix = stripped[: -len(unit_text)]
            if _NUMERIC_PREFIX_RE.fullmatch(prefix):
                return True
    return False


def _is_safe_simple_unit_token(token_text: str) -> bool:
    stripped = token_text.strip()
    if not stripped or _looks_like_url_or_path(stripped) or not _has_numeric_prefix(stripped):
        return False

    for unit_text in sorted(SIMPLE_UNIT_MAP, key=len, reverse=True):
        if not stripped.endswith(unit_text):
            continue
        prefix = stripped[: -len(unit_text)]
        if not _NUMERIC_PREFIX_RE.fullmatch(prefix):
            continue
        return True
    return False


def _normalize_compound_units(text: str) -> str:
    if not _has_unit_markers(text):
        return text
    return text


def _normalize_special_symbol_units(text: str) -> str:
    if not _has_unit_markers(text):
        return text
    return text


def _normalize_simple_units(text: str) -> str:
    if not _has_unit_markers(text):
        return text
    return text


def _normalize_semantic_speed(text: str) -> str:
    unit_pattern = "|".join(sorted(map(re.escape, SEMANTIC_SPEED_UNIT_MAP), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)\s*(?P<unit>{unit_pattern})"
        rf"(?=$|[^A-Za-z0-9가-힣/])"
    )

    def _replace(match: re.Match[str]) -> str:
        candidate = match.group(0)
        if _looks_like_url_or_path(candidate):
            return candidate

        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return candidate

        return f"시속 {number_reading} {SEMANTIC_SPEED_UNIT_MAP[match.group('unit')]}"

    current = re.sub(pattern, _replace, text)
    return re.sub(
        rf"(?<![가-힣])(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})\s+(?P<unit>킬로미터|미터)\s+퍼\s+(?P<measure>아워|리터|세크)(?![가-힣])",
        lambda match: (
            f"시속 {match.group('number')} 킬로미터"
            if match.group("measure") == "아워"
            else (
                f"리터당 {match.group('number')} {match.group('unit')}"
                if match.group("measure") == "리터"
                else f"초속 {match.group('number')} {match.group('unit')}"
            )
        ),
        current,
    )


def _normalize_prefix_currency(text: str) -> str:
    currency_number_pattern = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\.\d)(?!,\d)(?!/[A-Za-z])"
    prefix_pattern = "|".join(sorted(map(re.escape, SEMANTIC_CURRENCY_PREFIX_MAP), key=len, reverse=True))
    suffix_pattern = prefix_pattern
    symbol_prefix_pattern = r"(?:\$|€|₩|￦|¥|￥|£)"
    symbol_suffix_pattern = symbol_prefix_pattern
    fallback_prefix_pattern = r"(?:유에스디|케이알더블유|이유알)"
    spaced_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<prefix>{prefix_pattern})\s+(?P<number>{currency_number_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    attached_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<prefix>{prefix_pattern})(?P<number>{currency_number_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    euro_suffix_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{currency_number_pattern}|{_KOREAN_NUMBER_TOKEN_CORE})\s*€"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    euro_code_suffix_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{currency_number_pattern}|{_KOREAN_NUMBER_TOKEN_CORE})\s*(?P<code>EUR|이유알)"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    symbol_prefix_spaced_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<prefix>{symbol_prefix_pattern})\s+(?P<number>{currency_number_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    symbol_prefix_attached_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<prefix>{symbol_prefix_pattern})(?P<number>{currency_number_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    code_suffix_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{currency_number_pattern})\s*(?P<code>{suffix_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    symbol_suffix_pattern_with_number = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{currency_number_pattern})\s*(?P<symbol>{symbol_suffix_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    symbol_prefix_korean_number_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<prefix>{symbol_prefix_pattern})\s*(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    symbol_suffix_korean_number_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})\s*(?P<symbol>{symbol_suffix_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )
    fallback_code_suffix_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})\s*(?P<code>{fallback_prefix_pattern})"
        rf"(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )

    symbol_currency_map = {
        "$": "달러",
        "€": "유로",
        "₩": "원",
        "￦": "원",
        "¥": "엔",
        "￥": "엔",
        "£": "파운드",
    }
    fallback_currency_map = {
        "유에스디": "달러",
        "케이알더블유": "원",
        "이유알": "유로",
    }
    no_decimal_codes = {"KRW", "JPY", "GBP"}
    no_decimal_symbols = {"₩", "￦", "¥", "￥", "£"}

    def _replace(match: re.Match[str]) -> str:
        normalized = normalize_number_text(match.group("number"))
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        if normalized is not None and "." in normalized and match.group("prefix") in no_decimal_codes:
            return match.group(0)
        if (
            match.group("prefix") == "KRW"
            and normalized is not None
            and normalized.startswith("1")
            and len(normalized) > 1
            and set(normalized[1:]) == {"0"}
            and (len(normalized) - 1) % 4 == 0
            and number_reading in {"만", "억", "조", "경"}
        ):
            number_reading = f"일{number_reading}"
        return f"{number_reading} {SEMANTIC_CURRENCY_PREFIX_MAP[match.group('prefix')]}{match.group('suffix')}"

    def _replace_symbol_prefix(match: re.Match[str]) -> str:
        normalized = normalize_number_text(match.group("number"))
        if normalized is not None and "." in normalized and match.group("prefix") in no_decimal_symbols:
            return match.group(0)
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        return f"{number_reading} {symbol_currency_map[match.group('prefix')]}{match.group('suffix')}"

    def _replace_code_suffix(match: re.Match[str]) -> str:
        normalized = normalize_number_text(match.group("number"))
        if normalized is not None and "." in normalized and match.group("code") in no_decimal_codes:
            return match.group(0)
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        return f"{number_reading} {SEMANTIC_CURRENCY_PREFIX_MAP[match.group('code')]}{match.group('suffix')}"

    def _replace_symbol_suffix(match: re.Match[str]) -> str:
        normalized = normalize_number_text(match.group("number"))
        if normalized is not None and "." in normalized and match.group("symbol") in no_decimal_symbols:
            return match.group(0)
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        return f"{number_reading} {symbol_currency_map[match.group('symbol')]}{match.group('suffix')}"

    def _replace_euro_suffix(match: re.Match[str]) -> str:
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        return f"{number_reading} 유로{match.group('suffix')}"

    current = re.sub(spaced_pattern, _replace, text)
    current = re.sub(attached_pattern, _replace, current)
    current = re.sub(symbol_prefix_spaced_pattern, _replace_symbol_prefix, current)
    current = re.sub(symbol_prefix_attached_pattern, _replace_symbol_prefix, current)
    current = re.sub(code_suffix_pattern, _replace_code_suffix, current)
    current = re.sub(symbol_suffix_pattern_with_number, _replace_symbol_suffix, current)
    current = re.sub(
        symbol_prefix_korean_number_pattern,
        lambda match: f"{match.group('number')} {symbol_currency_map[match.group('prefix')]}{match.group('suffix')}",
        current,
    )
    current = re.sub(
        symbol_suffix_korean_number_pattern,
        lambda match: f"{match.group('number')} {symbol_currency_map[match.group('symbol')]}{match.group('suffix')}",
        current,
    )
    current = re.sub(
        fallback_code_suffix_pattern,
        lambda match: f"{match.group('number')} {fallback_currency_map[match.group('code')]}{match.group('suffix')}",
        current,
    )
    current = re.sub(euro_suffix_pattern, _replace_euro_suffix, current)
    current = re.sub(
        rf"(?<![{_BOUNDARY_CLASS}])(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})\s*€(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)(?=$|[^{_BOUNDARY_CLASS}])",
        lambda match: f"{match.group('number')} 유로{match.group('suffix')}",
        current,
    )
    current = re.sub(
        euro_code_suffix_pattern,
        lambda match: (
            f"{read_number_ko(match.group('number')) if classify_numeric_pattern(match.group('number')) is not None else match.group('number')} 유로{match.group('suffix')}"
        ),
        current,
    )
    current = re.sub(
        rf"(?<![{_BOUNDARY_CLASS}])유에스디\s+(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE})(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)(?=$|[^{_BOUNDARY_CLASS}])",
        lambda match: (
            f"{read_number_ko(match.group('number')) if classify_numeric_pattern(match.group('number')) is not None else match.group('number')} 달러{match.group('suffix')}"
        ),
        current,
    )
    current = re.sub(
        rf"(?<![{_BOUNDARY_CLASS}])케이알더블유\s+(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE})(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)(?=$|[^{_BOUNDARY_CLASS}])",
        lambda match: (
            f"{'일' + match.group('number') if match.group('number') in {'만', '억', '조', '경'} else (read_number_ko(match.group('number')) if classify_numeric_pattern(match.group('number')) is not None else match.group('number'))} 원{match.group('suffix')}"
        ),
        current,
    )
    return re.sub(
        rf"(?<![{_BOUNDARY_CLASS}])이유알\s+(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE})(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)(?=$|[^{_BOUNDARY_CLASS}])",
        lambda match: (
            f"{read_number_ko(match.group('number')) if classify_numeric_pattern(match.group('number')) is not None else match.group('number')} 유로{match.group('suffix')}"
        ),
        current,
    )


def _normalize_special_prefix_terms(text: str) -> str:
    term_pattern = "|".join(sorted(map(re.escape, SEMANTIC_PREFIX_TERM_MAP), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<prefix>{term_pattern})\s+(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )

    def _replace(match: re.Match[str]) -> str:
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        return f"{SEMANTIC_PREFIX_TERM_MAP[match.group('prefix')]} {number_reading}"

    current = re.sub(pattern, _replace, text)
    current = re.sub(
        rf"(?<![{_BOUNDARY_CLASS}])Mach\s+(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})(?=$|[^{_BOUNDARY_CLASS}])",
        lambda match: f"마하 {match.group('number')}",
        current,
    )
    return re.sub(
        rf"(?<![{_BOUNDARY_CLASS}])log\s+(?P<number>{_KOREAN_NUMBER_TOKEN_CORE})(?=$|[^{_BOUNDARY_CLASS}])",
        lambda match: f"로그 {match.group('number')}",
        current,
    )


def _normalize_bps_family(text: str) -> str:
    unit_pattern = "|".join(sorted(map(re.escape, SEMANTIC_BPS_FAMILY_MAP), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)(?P<unit>{unit_pattern})"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )

    def _replace(match: re.Match[str]) -> str:
        number_reading = read_number_ko(match.group("number"))
        if number_reading is None:
            return match.group(0)
        return f"{number_reading} {SEMANTIC_BPS_FAMILY_MAP[match.group('unit')]}"

    return re.sub(pattern, _replace, text)


def _normalize_tilde_counter_ranges(text: str) -> str:
    suffix_pattern = "|".join(sorted(map(re.escape, SEMANTIC_TILDE_COUNTER_SUFFIXES), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<start>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)\s*~\s*(?P<end>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)"
        rf"(?P<suffix>{suffix_pattern})"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )

    def _replace(match: re.Match[str]) -> str:
        start_reading = read_number_ko(match.group("start"))
        end_reading = read_number_ko(match.group("end"))
        if start_reading is None or end_reading is None:
            return match.group(0)
        result = f"{start_reading}에서 {end_reading}{match.group('suffix')}"
        return _KOREAN_COUNTER_SPACING_RE.sub(r"\1 \2", result)

    return re.sub(pattern, _replace, text)


def _try_parse_temperature_expression(text: str) -> str | None:
    match = re.fullmatch(
        rf"(-?{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)(?:\s*)(℃|℉|ºC|ºF|º)",
        text,
    )
    if not match:
        return None

    number_text, unit_text = match.groups()
    is_negative = number_text.startswith("-")
    unsigned_number_text = number_text[1:] if is_negative else number_text
    number_reading = read_number_ko(unsigned_number_text)
    if number_reading is None:
        return None

    temperature_reading = f"영하 {number_reading}" if is_negative else number_reading
    if unit_text in {"℉", "ºF"}:
        return f"화씨 {temperature_reading}도"
    return f"{temperature_reading}도"


def _try_parse_core_speed_expression(text: str) -> str | None:
    match = re.fullmatch(
        rf"({NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)(?:\s*)({'|'.join(map(re.escape, _CORE_SPEED_READING_MAP))})",
        text,
    )
    if not match:
        return None

    number_text, unit_text = match.groups()
    number_reading = _read_number_in_context(number_text, "unit")
    if number_reading is None:
        return None

    speed_prefix, unit_reading = _CORE_SPEED_READING_MAP[unit_text]
    return f"{speed_prefix} {number_reading} {unit_reading}"


def _try_parse_registered_compound_unit(text: str) -> str | None:
    stripped = text.strip()
    if not stripped or _looks_like_url_or_path(stripped):
        return None

    standalone_numeric_required_units = {
        "km/L",
        "km/l",
        "km/ℓ",
        "㎞/L",
        "㎞/l",
        "㎞/ℓ",
        "m/L",
        "m/l",
        "m/ℓ",
        "km/s",
        "㎞/s",
    }
    if stripped in COMPOUND_UNIT_MAP and _is_safe_compound_unit_token(stripped):
        if stripped in standalone_numeric_required_units:
            return None
        return COMPOUND_UNIT_MAP[stripped]

    for unit_text in sorted(COMPOUND_UNIT_MAP, key=len, reverse=True):
        if not stripped.endswith(unit_text):
            continue

        number_text = stripped[: -len(unit_text)].strip()
        if not number_text:
            continue

        if not _is_safe_compound_unit_token(stripped):
            return None

        number_reading = _read_number_in_context(number_text, "unit")
        if number_reading is None:
            return None
        # Whitelist-only speed readings stay narrow by design:
        # km/h/㎞/h -> 시속, m/s -> 초속, m/min -> 분속.
        if unit_text in _CORE_SPEED_READING_MAP:
            return _try_parse_core_speed_expression(stripped)

        return f"{number_reading} {COMPOUND_UNIT_MAP[unit_text]}"

    return None


def _try_parse_registered_special_unit(text: str) -> str | None:
    stripped = text.strip()
    if not stripped or _looks_like_url_or_path(stripped):
        return None

    if stripped in SPECIAL_UNIT_MAP and _is_safe_special_unit_token(stripped):
        return SPECIAL_UNIT_MAP[stripped]

    for unit_text in sorted(SPECIAL_UNIT_MAP, key=len, reverse=True):
        if not stripped.endswith(unit_text):
            continue

        number_text = stripped[: -len(unit_text)].strip()
        if not number_text:
            continue

        if not _is_safe_special_unit_token(stripped):
            return None

        number_reading = _read_number_in_context(number_text, "unit")
        if number_reading is None:
            return None

        return f"{number_reading} {SPECIAL_UNIT_MAP[unit_text]}"

    return None


def _try_parse_natural_compound_unit(text: str) -> str | None:
    # Natural compound units are checked before broader unit parsing.
    # Unsupported slash patterns are intentionally left to existing logic.
    stripped = text.strip()
    if not stripped or _looks_like_url_or_path(stripped):
        return None

    unit_pattern = "|".join(sorted(map(re.escape, _CORE_SPEED_READING_MAP), key=len, reverse=True))
    match = re.fullmatch(
        rf"(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)(?:\s?)(?P<unit>{unit_pattern})",
        stripped,
    )
    if not match:
        return None

    number_reading = _read_number_in_context(match.group("number"), "unit")
    if number_reading is None:
        return None

    prefix_reading, unit_reading = _CORE_SPEED_READING_MAP[match.group("unit")]
    return f"{prefix_reading} {number_reading} {unit_reading}"


def _try_parse_symbolic_area_volume_unit(text: str) -> str | None:
    # Geometry symbolic units stay narrow exact-pattern handlers.
    stripped = text.strip()
    if not stripped:
        return None

    geometry_unit_map = {
        "㎡": "제곱미터",
        "㎥": "세제곱미터",
        "m2": "제곱미터",
        "m3": "세제곱미터",
        "m^2": "제곱미터",
        "m^3": "세제곱미터",
    }
    unit_pattern = "|".join(sorted(map(re.escape, geometry_unit_map), key=len, reverse=True))
    match = re.fullmatch(
        rf"(?:(?P<number>{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?)\s?(?P<unit>{unit_pattern})(?P<suffix>(?:{_TRAILING_KO_PATTERN})*)|(?P<standalone>{unit_pattern}))",
        stripped,
    )
    if not match:
        return None

    standalone = match.group("standalone")
    if standalone is not None:
        return geometry_unit_map[standalone]

    normalized_number = normalize_number_text(match.group("number"))
    if normalized_number is None:
        return None
    if match.group("unit") in {"m2", "m3"} and "." not in normalized_number and len(normalized_number) < 2:
        return None

    number_reading = _read_number_in_context(match.group("number"), "unit")
    if number_reading is None:
        return None
    return f"{number_reading} {geometry_unit_map[match.group('unit')]}{match.group('suffix')}"


def _try_parse_numeric_unit_router(text: str) -> str | None:
    # Shared entry point for exact supported numeric-unit forms only.
    return _try_parse_natural_compound_unit(text) or _try_parse_symbolic_area_volume_unit(text)


def _read_number_in_context(text: str, category: str) -> str | None:
    normalized = normalize_number_text(text)
    if normalized is None:
        return None
    if _NORMALIZED_INTEGER_RE.fullmatch(normalized):
        return read_number_token_ko(normalized, {"category": category})
    return read_number_ko(normalized)


def _try_parse_registered_simple_unit(text: str) -> str | None:
    stripped = text.strip()
    if not stripped or _looks_like_url_or_path(stripped) or not _is_safe_simple_unit_token(stripped):
        return None

    for unit_text in sorted(SIMPLE_UNIT_MAP, key=len, reverse=True):
        if unit_text in _LIVE_SIMPLE_UNIT_SKIP or not stripped.endswith(unit_text):
            continue

        number_text = stripped[: -len(unit_text)].strip()
        if not number_text:
            continue

        number_reading = _read_number_in_context(number_text, "unit")
        if number_reading is None:
            return None

        reading = SIMPLE_UNIT_MAP[unit_text]
        if unit_text in ("도", "원", "층", "호", "동", "년", "월", "일", "회", "번"):
            return f"{number_reading}{reading}"
        return f"{number_reading} {reading}"

    return None


TIME_COLON_RULE = Rule(
    name="time_colon",
    pattern=r"(?:(?:오전|오후|새벽|아침|정오|밤|저녁)\s*)?\d{1,2}:\d{2}(?::\d{2})?",
    parser=try_parse_time,
    gate_name="time_colon_context",
)

TIME_HOUR_KOREAN_RULE = Rule(
    name="time_hour_korean",
    pattern=r"\d{1,2}시",
    parser=try_parse_time,
    gate_name="time_hour_korean_context",
)

DECIMAL_RULE = Rule(
    name="decimal",
    pattern=rf"(?<!\d,){NUMERIC_INTEGER_PATTERN}\.\d+(?!\.\d)",
    parser=_try_parse_decimal,
    allow_josa=False,
    gate_name="decimal_context",
)

UNIT_RULE = Rule(
    name="unit",
    pattern=rf"(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s*{_BASIC_UNIT_SUFFIX_CORE}{_UNIT_PARTICLE_SUFFIX_CORE})",
    parser=try_parse_basic_unit,
    gate_name="unit_context",
)


def _apply_time_rules(text: str, ctx: RuleContext | None = None) -> str:
    _assert_rule_stage("date_time")
    if not any(trigger in text for trigger in _TIME_TRIGGER_TOKENS):
        return text

    # Time stays conservative: exact clock-like "H시", "H시 M분", and
    # "H시 M분 S초" forms are handled here, while attached Korean-text
    # ambiguities such as "3시리즈" remain outside this path.
    korean_patterns = [
        _build_rule_pattern(r"\d{1,2}시\s*\d{1,2}분\s*\d{1,2}초"),
        _build_rule_pattern(r"\d{1,2}시\s*\d{1,2}분"),
        _build_rule_pattern(r"\d{1,2}시\s*\d{1,2}초"),
    ]

    current = apply_rule(text, TIME_COLON_RULE, ctx)

    current = _apply_pattern(current, korean_patterns[0], try_parse_time)
    current = _apply_pattern(current, korean_patterns[1], try_parse_time)
    current = _apply_pattern(current, korean_patterns[2], try_parse_time)
    current = apply_rule(current, TIME_HOUR_KOREAN_RULE, ctx)
    return current


def _apply_middle_dot_structured_rules(text: str) -> str:
    _assert_rule_stage("middle_dot_structured")
    return _apply_pattern(
        text,
        _build_rule_pattern(r"\d+(?:·\d+)+"),
        try_parse_middle_dot_structured,
    )


def _apply_spaced_middle_dot_rules(text: str) -> str:
    _assert_rule_stage("spaced_middle_dot")
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?P<left>{NUMERIC_INTEGER_PATTERN})\s+·\s+(?P<right>{NUMERIC_INTEGER_PATTERN})"
        rf"(?P<tail>(?:{_TRAILING_KO_PATTERN})*)"
        rf"(?=$|[^{_BOUNDARY_CLASS}])"
    )

    def _replace(match: re.Match[str]) -> str:
        left_reading = read_number_token_ko(match.group("left"))
        right_reading = read_number_token_ko(match.group("right"))
        if left_reading is None or right_reading is None:
            return match.group(0)
        return f"{left_reading} · {right_reading}{match.group('tail')}"

    return re.sub(pattern, _replace, text)


def _try_parse_integer(text: str) -> str | None:
    if "~" in text:
        return None

    if classify_numeric_pattern(text) not in {"comma_integer", "plain_integer"}:
        return None

    normalized = normalize_number_text(text)
    if normalized is None or not _NORMALIZED_INTEGER_RE.fullmatch(normalized):
        return None
    return read_number_token_ko(normalized)


def _try_parse_decimal_with_suffix(text: str) -> str | None:
    match = re.fullmatch(rf"({NUMERIC_INTEGER_PATTERN}\.\d+)([가-힣]+)", text)
    if not match:
        return None

    number_text, suffix_text = match.groups()
    if _PURE_TRAILING_KO_PATTERN.fullmatch(suffix_text):
        return None
    normalized = normalize_number_text(number_text)
    if normalized is None or not _has_supported_fractional_length(normalized):
        return None

    number_reading = read_number_ko(number_text)
    if number_reading is None:
        return None

    return f"{number_reading} {suffix_text}"


def _try_parse_decimal_with_trailing_particle(text: str) -> str | None:
    match = re.fullmatch(rf"({NUMERIC_INTEGER_PATTERN}\.\d+)((?:{_TRAILING_KO_PATTERN})+)", text)
    if not match:
        return None

    number_text, suffix_text = match.groups()
    number_reading = _try_parse_decimal(number_text)
    if number_reading is None:
        return None
    return f"{number_reading}{suffix_text}"


def _try_parse_large_unit_atomic_expression(text: str) -> str | None:
    match = re.fullmatch(rf"({NUMERIC_INTEGER_PATTERN})(억|조|경|해)", text)
    if not match:
        return None

    number_text, unit_text = match.groups()
    normalized = normalize_number_text(number_text)
    if normalized is None or "." in normalized:
        return None
    return f"{read_integer_ko(normalized)}{unit_text}"


def _try_parse_hyphen_digit_blocks(text: str) -> str | None:
    # Only whitespace-free 3-to-5 block numeric hyphen forms are handled here.
    # Two-block patterns are intentionally excluded from this policy.
    if _HYPHEN_DIGIT_BLOCKS_RE.fullmatch(text) is None:
        return None

    blocks = text.split("-")
    if not (3 <= len(blocks) <= 9):
        return None

    # For exact 4-2-2 three-block forms, date parsing gets priority first.
    # If that fails, we fall back to per-digit block reading below.
    if len(blocks) == 3 and [len(block) for block in blocks] == [4, 2, 2]:
        date_reading = try_parse_date(text)
        if date_reading is not None:
            return date_reading

    # Non-date fallback reads each digit individually, with 0 spoken as 공,
    # and joins the block readings with a single space.
    return " ".join("".join(PHONE_DIGIT_KO[digit] for digit in block) for block in blocks)


def _split_tilde_context(candidate: str) -> tuple[str, str] | None:
    if "~" not in candidate or candidate.count("~") != 1:
        return None

    left_text, right_text = candidate.split("~", 1)
    left_text = left_text.strip()
    right_text = right_text.strip()
    if not left_text or not right_text:
        return None
    return left_text, right_text


def _is_valid_tilde_range(left_text: str, right_text: str) -> bool:
    # Treat "~" as a range marker only in numeric-like contexts.
    left = left_text.strip()
    right = right_text.strip()
    if not left or not right:
        return False

    left_kind = classify_numeric_pattern(left)
    right_kind = classify_numeric_pattern(right)
    return left_kind is not None and right_kind is not None


def _try_parse_spoken_range(text: str) -> str | None:
    match = re.fullmatch(
        rf"((?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE}))\s*~\s*((?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE}))(\s*(?:{_DURATION_UNIT_SUFFIX_CORE}|{_BASIC_UNIT_SUFFIX_CORE}|{_FILESIZE_UNIT_SUFFIX_CORE}|[가-힣]+))?",
        text,
    )
    if not match:
        return None

    start_text, end_text, suffix_text = match.groups()
    if suffix_text is None and end_text.endswith("쪽"):
        end_text = end_text[:-1]
        suffix_text = "쪽"

    def _resolve_counter_value(token: str) -> int | None:
        normalized = normalize_number_text(token)
        if normalized is not None and "." not in normalized:
            return int(normalized)
        for value in range(1, 100):
            if read_integer_ko(str(value)) == token:
                return value
        return None

    start_reading = read_number_ko(start_text) if classify_numeric_pattern(start_text) is not None else start_text
    end_reading = read_number_ko(end_text) if classify_numeric_pattern(end_text) is not None else end_text
    if start_reading is None or end_reading is None:
        return None

    if not suffix_text:
        return f"{start_reading}에서 {end_reading}"

    stripped_suffix = suffix_text.strip()
    if re.fullmatch(rf"\s*(?:{_DURATION_UNIT_SUFFIX_CORE}|{_BASIC_UNIT_SUFFIX_CORE}|{_FILESIZE_UNIT_SUFFIX_CORE})", suffix_text):
        return f"{start_reading}에서 {end_text}{suffix_text}"

    result = f"{start_reading}에서 {end_reading}{suffix_text}"
    if stripped_suffix.startswith("쪽"):
        return f"{start_reading}에서 {end_reading} {suffix_text.lstrip()}"
    return result


# USER.md: 2-6 날짜 구간 읽기
def _apply_date_range_rules(text: str) -> str:
    _assert_rule_stage("date_range")
    if "~" not in text:
        return text
    if not any(trigger in text for trigger in _DATE_TRIGGER_TOKENS):
        return text

    patterns = [
        _build_rule_pattern(r"\d{4}\s*~\s*\d{4}년"),
        _build_rule_pattern(r"\d{4}년\s*~\s*\d{4}년"),
        _build_rule_pattern(r"\d{4}[./-]\d{1,2}[./-]\d{1,2}~\d{4}[./-]\d{1,2}[./-]\d{1,2}"),
        _build_rule_pattern(r"\d{1,2}월\s*\d{1,2}일~\d{1,2}월\s*\d{1,2}일"),
    ]

    current = text
    for pattern in patterns[:2]:
        current = _apply_pattern(current, pattern, try_parse_year_range)
    for pattern in patterns[2:]:
        current = _apply_pattern(current, pattern, try_parse_date_range)
    return current


def _apply_hyphen_digit_block_rules(text: str) -> str:
    _assert_rule_stage("hyphen_digit_blocks")
    if "-" not in text or not any(char.isdigit() for char in text):
        return text

    regex = re.compile(_build_rule_pattern(r"\d{1,8}(?:-\d{1,8}){2,8}"))

    def _replace(match: re.Match[str]) -> str:
        candidate = match.group(0)
        decision = GATE_REGISTRY.evaluate(
            "hyphen_digit_block_routing",
            candidate=candidate,
            text=text,
            start=match.start(),
            end=match.end(),
        )
        if not decision.allowed:
            return candidate
        parsed = _try_parse_hyphen_digit_blocks(candidate)
        return parsed if parsed is not None else candidate

    return regex.sub(_replace, text)


# USER.md: 2-5 날짜 읽기, 2-7 시간 읽기
def _apply_date_time_rules(text: str, ctx: RuleContext | None = None) -> str:
    _assert_rule_stage("date_time")
    if not any(trigger in text for trigger in _DATE_TRIGGER_TOKENS):
        return _apply_time_rules(text, ctx)

    patterns = [
        (_build_rule_pattern(r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"), _try_parse_date_by_slash_context),
        (_build_rule_pattern(r"\d{4}년\s*\d{1,2}월\s*\d{1,2}일"), try_parse_date),
        (_build_rule_pattern(r"\d{1,2}월\s*\d{1,2}일"), try_parse_date),
    ]

    current = text
    for pattern, parser in patterns:
        current = _apply_pattern(current, pattern, parser)
    return _apply_time_rules(current, ctx)


# USER.md: 2-9 퍼센트 읽기, 2-10 퍼센트포인트 읽기, 2-11 온도 읽기, 2-13 화폐 읽기
def _apply_percent_temperature_currency_rules(text: str) -> str:
    _assert_rule_stage("percent_currency")
    if not any(trigger in text for trigger in _PERCENT_TEMPERATURE_CURRENCY_TRIGGERS):
        return text

    currency_number_pattern = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\.\d)(?!,\d)(?!/[A-Za-z])"
    # Temperature-specific negative has higher priority than generic minus for
    # supported temperature units, including josa chains such as "로도".
    temperature_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}])"
        rf"(?:-?(?:\d+|\d{{1,3}}(?:,\d{{3}})+)(?:\.\d+)?(?:\s*)(?:℃|℉|ºC|ºF|º))"
        rf"(?=(?:{_TRAILING_KO_PATTERN})+(?![{_BOUNDARY_CLASS}])|$|[^{_BOUNDARY_CLASS}])"
    )

    patterns = [
        (_build_rule_pattern(r"\d+(?:\.\d+)?%p"), try_parse_percent_point),
        (_build_rule_pattern(r"\d+(?:\.\d+)?%"), try_parse_percent),
        (_build_rule_pattern(rf"-(?:\d+|\d{{1,3}}(?:,\d{{3}})+)(?:\.\d+)?(?:\s*)도"), try_parse_signed_degree_quantity),
        (temperature_pattern, _try_parse_temperature_expression),
        (_build_rule_pattern(r"\d+(?:\.\d+)?(?:만|억|조)\s*원"), try_parse_compact_krw),
        (_build_rule_pattern(r"₩(?:\d{1,3}(?:,\d{3})+|\d+)(?!\.\d)|(?:\d{1,3}(?:,\d{3})+|\d+)원"), try_parse_krw),
        (_build_rule_pattern(rf"\${currency_number_pattern}"), try_parse_usd),
        (_build_rule_pattern(rf"€{currency_number_pattern}"), try_parse_eur),
        (_build_rule_pattern(rf"[￥¥](?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?!\.\d)(?!,\d)(?!/[A-Za-z])"), try_parse_jpy),
        (_build_rule_pattern(rf"£(?:\d{{1,3}}(?:,\d{{3}})+|\d+)(?!\.\d)(?!,\d)(?!/[A-Za-z])"), try_parse_gbp),
    ]

    current = text
    for pattern, parser in patterns:
        current = _apply_pattern(current, pattern, parser)
    return current


# USER.md: 2-1 정수 숫자 읽기, 2-2 소수 읽기, 2-3 음수 읽기, 2-4 분수 읽기
def _apply_fraction_rules(text: str) -> str:
    _assert_rule_stage("fraction")
    if "/" not in text:
        return text

    return _apply_pattern(
        text,
        _build_rule_pattern(r"\d+/\d+"),
        _try_parse_fraction_by_slash_context,
    )


def _apply_compound_unit_rules(text: str) -> str:
    _assert_rule_stage("compound_unit")
    if not any(trigger in text for trigger in _COMPOUND_UNIT_TRIGGERS):
        return text

    # Live order is compound > special > simple so exact slash-based compound
    # units get first chance before generic slash or broader unit paths.
    natural_compound_pattern = "|".join(sorted(map(re.escape, _CORE_SPEED_READING_MAP), key=len, reverse=True))
    natural_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s?(?:{natural_compound_pattern})"
        rf"(?=$|[^A-Za-z0-9가-힣/])"
    )
    current = _apply_pattern(text, natural_pattern, _try_parse_natural_compound_unit)

    compound_pattern = "|".join(sorted(map(re.escape, COMPOUND_UNIT_MAP), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s*)?(?:{compound_pattern})"
        rf"(?=$|[^A-Za-z0-9가-힣/])"
    )
    current = _apply_pattern(current, pattern, _try_parse_registered_compound_unit)
    if not any(trigger in current for trigger in _CORE_SPEED_TRIGGERS):
        return current

    core_speed_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s*)(?:km/h|㎞/h|km/L|km/l|km/ℓ|㎞/L|㎞/l|㎞/ℓ|m/L|m/l|m/ℓ|m/s|km/s|㎞/s|m/min)"
        rf"(?=(?:{_TRAILING_KO_PATTERN})(?![{_BOUNDARY_CLASS}])|$)"
    )
    return _apply_pattern(current, core_speed_pattern, _try_parse_core_speed_expression)


def _apply_special_unit_rules(text: str) -> str:
    _assert_rule_stage("special_unit")
    if not any(trigger in text for trigger in (*_SPECIAL_UNIT_TRIGGERS, "m2", "m3", "m^2", "m^3")):
        return text

    geometry_pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s?(?:㎡|㎥|m2|m3|m\^2|m\^3)(?:{_TRAILING_KO_PATTERN})*|㎡|㎥|m2|m3|m\^2|m\^3)"
        rf"(?=$|[^A-Za-z0-9가-힣/]|(?:{_TRAILING_KO_PATTERN})(?![{_BOUNDARY_CLASS}]))"
    )
    current = _apply_pattern(text, geometry_pattern, _try_parse_symbolic_area_volume_unit)

    # Special symbols may stand alone, but only for exact registered tokens.
    special_pattern = "|".join(sorted(map(re.escape, SPECIAL_UNIT_MAP), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s*)?(?:{special_pattern})"
        rf"(?=$|[^A-Za-z0-9가-힣/])"
    )
    return _apply_pattern(current, pattern, _try_parse_registered_special_unit)


def _apply_simple_unit_rules(text: str) -> str:
    _assert_rule_stage("simple_unit")
    if not any(trigger in text for trigger in _SIMPLE_UNIT_TRIGGERS):
        return text

    # Simple units require a numeric prefix; standalone unit strings stay
    # untouched so unknown/risky contexts can defer to older behavior.
    live_simple_units = {
        unit: reading for unit, reading in SIMPLE_UNIT_MAP.items() if unit not in _LIVE_SIMPLE_UNIT_SKIP
    }
    simple_pattern = "|".join(sorted(map(re.escape, live_simple_units), key=len, reverse=True))
    pattern = (
        rf"(?<![{_BOUNDARY_CLASS}/])"
        rf"{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s*(?:{simple_pattern})"
        rf"(?=$|[^A-Za-z0-9가-힣/])"
    )
    return _apply_pattern(text, pattern, _try_parse_registered_simple_unit)


# USER.md: 2-1 정수 숫자 읽기, 2-2 소수 읽기, 2-3 음수 읽기, 2-4 분수 읽기
def _apply_number_rules(text: str, ctx: RuleContext | None = None) -> str:
    _assert_rule_stage("number")
    if "~" not in text and "." not in text and "-" not in text and not any(char.isdigit() for char in text):
        return text

    negative_pattern = _build_rule_pattern(rf"(?<![$€₩￦¥￥£])-{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?", allow_josa=False)
    trailing_patterns = [
        (
            _build_rule_pattern(rf"{NUMERIC_INTEGER_PATTERN}(?:억|조|경|해)"),
            _try_parse_large_unit_atomic_expression,
        ),
        (
            _build_rule_pattern(rf"(?<!\d-){NUMERIC_INTEGER_PATTERN}\.\d+(?:{_TRAILING_KO_PATTERN})+", allow_josa=False),
            _try_parse_decimal_with_trailing_particle,
        ),
        (
            _build_rule_pattern(
                rf"-?{NUMERIC_INTEGER_PATTERN}\.\d+(?:\s*)(?:도|{_BASIC_UNIT_SUFFIX_CORE}|{_FILESIZE_UNIT_SUFFIX_CORE})(?!/[A-Za-z])"
            ),
            try_parse_decimal_attached_unit,
        ),
        (
            # Two-block numeric hyphen + Korean unit is preserved as-is due to
            # ambiguity (range/chapter/identifier).
            _build_rule_pattern(rf"(?<!\d-){NUMERIC_INTEGER_PATTERN}\.\d+[가-힣]+", allow_josa=False),
            _try_parse_decimal_with_suffix,
        ),
        (
            _build_rule_pattern(rf"(?<!\d-){NUMERIC_INTEGER_PATTERN}(?:\.\d+)?[가-힣]+"),
            try_parse_comma_number_with_suffix,
        ),
        (
            _build_rule_pattern(
                rf"(?<![\d:.,#$€₩￦¥￥£A-Za-z-]){NUMERIC_INTEGER_PATTERN}(?!,\d)(?!\.\d)(?![:-]\d)(?![A-Za-z])",
                allow_josa=False,
            ),
            lambda candidate: (
                candidate
                if re.match(rf"{re.escape(candidate)}\s?(?:㎡|㎥|m2|m3)[A-Za-z]", text)
                else _try_parse_integer(candidate)
            ),
        ),
    ]

    # Negative numbers own the "-<number>" form before decimal fallback so
    # plain negatives do not leak into positive decimal parsing.
    current = _apply_pattern(text, negative_pattern, read_negative_ko)
    current = _apply_plain_12_3_decimal_rules(current)
    current = apply_rule(current, DECIMAL_RULE, ctx)

    for pattern, parser in trailing_patterns:
        current = _apply_pattern(current, pattern, parser)
    return current


# USER.md: 2-8 기간 단위 읽기
def _apply_duration_rules(text: str) -> str:
    _assert_rule_stage("duration")
    if not any(trigger in text for trigger in _DURATION_UNIT_TRIGGERS):
        return text

    return _apply_pattern(
        text,
        _build_rule_pattern(rf"\d+(?:\.\d+)?\s*{_DURATION_UNIT_SUFFIX_CORE}"),
        try_parse_duration,
    )


# USER.md: 2-12 숫자+단위 읽기, 2-14 파일 크기 읽기
def _apply_unit_rules(text: str, ctx: RuleContext | None = None) -> str:
    _assert_rule_stage("unit")
    if not any(char.isdigit() for char in text):
        return text
    if not any(trigger in text for trigger in (*_FILESIZE_UNIT_TRIGGERS, *_COUNTER_NOUN_TRIGGERS, *_SIMPLE_UNIT_TRIGGERS, "㎡", "m²", "㎥", "m³", "GB/s", "km/h", "㎞/h", "km/L", "km/l", "km/ℓ", "㎞/L", "㎞/l", "㎞/ℓ", "m/L", "m/l", "m/ℓ", "m/s", "km/s", "㎞/s", "kWh", "kW", "MHz", "GHz")):
        return apply_rule(text, UNIT_RULE, ctx)

    filesize_core = rf"{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s*{_FILESIZE_UNIT_SUFFIX_CORE}{_UNIT_PARTICLE_SUFFIX_CORE}"

    patterns = [
        (_build_rule_pattern(filesize_core), try_parse_filesize),
    ]

    current = apply_rule(text, UNIT_RULE, ctx)
    for pattern, parser in patterns:
        current = _apply_pattern(current, pattern, parser)
    return current


# USER.md: 2-15 전화번호 읽기, 2-16 pH 읽기, 2-17 각도 읽기
SPECIAL_RULES = RuleGroup(
    name="special",
    rules=(
        Rule("upper_decimal", r"[A-Z]+\s+\d+\.\d+", try_parse_upper_decimal_compound),
        Rule("phone", r"010-\d{4}-\d{4}|02-\d{3}-\d{4}|\d{4}-\d{4}", try_parse_phone, gate_name="hyphen_phone_routing"),
        Rule("ph", r"pH\s*\d+(?:\.\d+)?(?![.\dA-Za-z])", try_parse_ph, gate_name="no_preceding_ascii_alpha"),
        Rule("angle", r"\d+°", try_parse_angle),
    ),
)


def _apply_special_rules(text: str, ctx: RuleContext | None = None) -> str:
    _assert_rule_stage("special")
    if not any(trigger in text for trigger in _SPECIAL_RULE_TRIGGERS):
        return text

    return apply_rule_group(text, SPECIAL_RULES, ctx)


def _apply_final_spoken_range_rules(text: str) -> str:
    _assert_rule_stage("final_range")
    if "~" not in text:
        return text

    # Tilde is a late authority: earlier number/unit passes must leave "~"
    # ranges untouched so this stage is the single deterministic owner.
    # Only numeric or already-spoken Korean-number candidates are handled
    # here; non-range tilde usage such as greetings/emphasis is preserved.
    return _apply_pattern(
        text,
        _build_rule_pattern(
            rf"(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE})\s*~\s*(?:{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?|{_KOREAN_NUMBER_TOKEN_CORE})(?:\s*(?:{_DURATION_UNIT_SUFFIX_CORE}|{_BASIC_UNIT_SUFFIX_CORE}|{_FILESIZE_UNIT_SUFFIX_CORE}|[가-힣]+))?",
            allow_josa=False,
        ),
        _try_parse_spoken_range,
    )


RULE_PIPELINE = (
    RuleStage(
        "date_range",
        lambda text, ctx: _apply_date_range_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("tilde date range", "tilde year range"),
    ),
    RuleStage(
        "hyphen_digit_blocks",
        lambda text, ctx: _apply_hyphen_digit_block_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("pure numeric multi-block hyphen",),
    ),
    RuleStage(
        "date_time",
        lambda text, ctx: _apply_date_time_rules(text, ctx),
        RuleStageRole.STRUCTURED_PARSER,
        ("calendar date", "time colon", "korean time expression"),
    ),
    RuleStage(
        "special_unit",
        lambda text, ctx: _apply_special_unit_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("registered special unit", "symbolic area/volume unit"),
        precondition=lambda text, ctx: _has_unit_markers(text),
    ),
    RuleStage(
        "special",
        lambda text, ctx: _apply_special_rules(text, ctx),
        RuleStageRole.STRUCTURED_PARSER,
        ("phone", "pH", "angle", "upper decimal compound"),
    ),
    RuleStage(
        "emergency",
        lambda text, ctx: _apply_emergency_number_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("112/119 with emergency context",),
    ),
    RuleStage(
        "percent_currency",
        lambda text, ctx: _apply_percent_temperature_currency_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("percent", "temperature", "currency"),
        precondition=lambda text, ctx: any(marker in text for marker in ("%", "원", "$", "€", "¥", "￥", "₩", "℃", "℉", "º", "도")),
    ),
    RuleStage(
        "compound_unit",
        lambda text, ctx: _apply_compound_unit_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("slash compound unit", "speed/efficiency unit"),
        precondition=lambda text, ctx: _has_unit_markers(text),
    ),
    RuleStage(
        "simple_unit",
        lambda text, ctx: _apply_simple_unit_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("simple numeric unit",),
        precondition=lambda text, ctx: _has_unit_markers(text),
    ),
    RuleStage(
        "fraction",
        lambda text, ctx: _apply_fraction_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("slash fraction",),
        precondition=lambda text, ctx: "/" in text,
    ),
    RuleStage(
        "counter_noun",
        lambda text, ctx: _apply_counter_noun_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("native/sino counter noun",),
    ),
    RuleStage(
        "duration",
        lambda text, ctx: _apply_duration_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("duration unit",),
    ),
    RuleStage(
        "unit",
        lambda text, ctx: _apply_unit_rules(text, ctx),
        RuleStageRole.STRUCTURED_PARSER,
        ("general numeric unit", "filesize"),
        precondition=lambda text, ctx: any(char.isdigit() for char in text),
    ),
    RuleStage(
        "spaced_middle_dot",
        lambda text, ctx: _apply_spaced_middle_dot_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("spaced middle dot numeric pair",),
        precondition=lambda text, ctx: " · " in text,
    ),
    RuleStage(
        "middle_dot_structured",
        lambda text, ctx: _apply_middle_dot_structured_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("contiguous middle dot numeric chain",),
        precondition=lambda text, ctx: "·" in text,
    ),
    RuleStage(
        "number",
        lambda text, ctx: _apply_number_rules(text, ctx),
        RuleStageRole.STRUCTURED_PARSER,
        ("plain integer", "plain decimal", "negative number", "large-unit atomic"),
    ),
    RuleStage(
        "final_range",
        lambda text, ctx: _apply_final_spoken_range_rules(text),
        RuleStageRole.STRUCTURED_PARSER,
        ("spoken tilde range", "shared-suffix tilde range"),
        precondition=lambda text, ctx: "~" in text,
    ),
)


def prepare_rule_context(text: str, gate_logs: list[str] | None = None) -> RuleContext:
    preprocessed = _preprocess(text)
    tokens = tokenize(preprocessed)
    tokenized_text = "".join(token.text for token in tokens)
    return RuleContext(
        original_text=text,
        preprocessed_text=preprocessed,
        tokenized_text=tokenized_text,
        tokens=tokens,
        gate_logs=gate_logs if gate_logs is not None else [],
    )


def run_rule_pipeline(ctx: RuleContext) -> str:
    # USER.md: 1-1 처리 우선순위
    # Add new USER.md rules here in the same order as the document sections.
    current = ctx.tokenized_text
    for stage in RULE_PIPELINE:
        if stage.precondition is not None:
            if not stage.precondition(current, ctx):
                continue
        token = _ACTIVE_RULE_STAGE.set(stage.name)
        try:
            current = stage.runner(current, ctx)
        finally:
            _ACTIVE_RULE_STAGE.reset(token)
    return current


def finalize_rule_output(current: str, ctx: RuleContext) -> str:
    return _restore_event_dot_expressions(current)


def apply_rules(text: str, gate_logs: list[str] | None = None) -> str:
    if re.fullmatch(rf"-?{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?\s+(?:pH|Mach)", text):
        return text

    if re.fullmatch(rf"(?:pH|Mach|log)\s+{NUMERIC_INTEGER_PATTERN}(?:\.\d+)?", text):
        return _normalize_special_prefix_terms(text)

    protected_text, url_replacements = _protect_urls(text)
    shared_gate_logs = gate_logs if gate_logs is not None else []
    with gate_log_scope(shared_gate_logs):
        ctx = prepare_rule_context(protected_text, gate_logs=shared_gate_logs)
        current = run_rule_pipeline(ctx)
        current = finalize_rule_output(current, ctx)
        # Remaining post-rule normalization stays narrow and whitelist-based.
        # USD/KRW prefix currency is handled here without broadening generic
        # acronym, symbol, or non-whitelisted code behavior.
        current = _normalize_prefix_currency(current)
        return _restore_urls(current, url_replacements)
