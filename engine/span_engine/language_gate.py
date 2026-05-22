from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from engine.span_engine.currency import (
    CURRENCY_CODE_READINGS,
    CURRENCY_SYMBOL_READINGS,
    KOREAN_CURRENCY_SUFFIX_READINGS,
)
from engine.span_engine.protected import (
    is_standalone_protected_literal,
    mask_protected_literals,
)

_HANGUL_SYLLABLE_RE = re.compile(r"[가-힣]")
_EMAIL_RE = re.compile(r"\b[^@\s]+@[^@\s]+\.[^@\s]+\b")
_SHELL_PREFIXES = (
    "curl ",
    "python ",
    "python3 ",
    "bash ",
    "sh ",
    "cd ",
    "export ",
    "ssh ",
    "rsync ",
    "git ",
)
_CODE_PREFIXES = ("const ", "let ", "var ", "def ", "class ", "function ")
_URL_WHOLE_RE = re.compile(r"(?:https?://|www\.)\S+")

_SIGN = r"[+\-−－]?"
_INTEGER = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_DECIMAL = rf"{_INTEGER}(?:\.\d+)?"
_NUMBER_UNIT_GAP = r"[ ]?"
_SLASH = r"[/／⁄∕]"
_COMPOUND_SLASH = r"[/／]"
_PERCENT = r"[%％﹪]"
_TEMP_UNIT = r"(?:℃|℉|º|ºC|ºF|°C|°F|°\s*C|°\s*F|º\s*C|º\s*F)"
_SIMPLE_UNIT = (
    r"(?:㎠|㎢|㎤|㎦|㎜|㎝|㎞|㎎|㎏|㎖|㎡|㎥|㎐|㎒|㎓|㏈|"
    r"m²|cm²|km²|m³|cm³|km³|m3|cm3|km3|kHz|MHz|GHz|Ghz|ghz|mL|ml|ML|kWh|mm|cm|km|"
    r"mg|kg|Hz|hz|dB|KB|MB|GB|PB|m|g|L|%)"
)
_COMPOUND_UNIT = (
    r"(?:km|㎞|m|cm|㎝|mg|㎎|g|KB|MB|GB|TB|PB)"
    rf"{_COMPOUND_SLASH}"
    r"(?:h|hr|min|s|sec|L|l|ℓ|dL)"
)
_EXACT_COMPOUND = r"(?:Mbps|Gbps|rpm|fps|ppm|ppb|dBi)"
_CURRENCY_PREFIX = r"[$＄﹩€₩￦¥￥£]"
_CURRENCY_SUFFIX = r"(?:USD|EUR|KRW|JPY|GBP|원|[$＄﹩€₩￦¥￥£])"
_CURRENCY_CODE = r"(?:USD|EUR|KRW|JPY|GBP)"
_TIME = r"\d{1,2}[:：]\d{2}"
_DATE = r"\d{4}(?:[-/.]|／)\d{2}(?:[-/.]|／)\d{2}"
_DECIMAL_TOKEN = rf"{_INTEGER}\.\d+"
_SIGNED_NUMBER_TOKEN = rf"[+\-−－]{_DECIMAL}"
_MIDDLE_DOT_TOKEN = rf"{_INTEGER}·{_INTEGER}"
_TWO_BLOCK_HYPHEN_CODE = rf"[A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ]+-{_DECIMAL}"
_SPACED_FREQUENCY = rf"{_DECIMAL}\s+(?:Hz|hz)"
_PH_SUFFIX_POSITION = rf"{_DECIMAL}\s+pH"
_RANGE = rf"{_DECIMAL}[~∼～〜]{_DECIMAL}(?:{_SIMPLE_UNIT}|[월일년층호동원도])?"
_DURATION = rf"(?:{_INTEGER}(?:\.\d+)?(?:{_SLASH}{_INTEGER})?시간(?:\s*{_INTEGER}(?:\.\d+)?(?:{_SLASH}{_INTEGER})?분)?|{_INTEGER}(?:\.\d+)?(?:{_SLASH}{_INTEGER})?분)"
_PH = rf"pH\s*{_DECIMAL}"
_FRACTION = rf"{_SIGN}{_INTEGER}{_SLASH}{_INTEGER}"
_PERCENT_POINT = rf"{_SIGN}(?:{_INTEGER}{_SLASH}{_INTEGER}|{_DECIMAL}){_PERCENT}p"
_PERCENT_TOKEN = rf"{_DECIMAL}{_PERCENT}"
_UNIT_TOKEN = rf"{_DECIMAL}{_NUMBER_UNIT_GAP}(?:{_TEMP_UNIT}|{_SIMPLE_UNIT}|{_EXACT_COMPOUND})"
_COMPOUND_TOKEN = rf"{_DECIMAL}{_NUMBER_UNIT_GAP}{_COMPOUND_UNIT}"
_CURRENCY_TOKEN = rf"(?:{_CURRENCY_PREFIX}{_NUMBER_UNIT_GAP}{_DECIMAL}|{_DECIMAL}{_NUMBER_UNIT_GAP}{_CURRENCY_SUFFIX}|{_CURRENCY_CODE}{_NUMBER_UNIT_GAP}{_DECIMAL})"
_SIGNED_DECIMAL_BLOCK = rf"[+\-]?{_DECIMAL}"
_MULTI_COLON_SURFACE = rf"{_SIGNED_DECIMAL_BLOCK}(?:[:：]{_SIGNED_DECIMAL_BLOCK}){{2,}}"
_HYPHENATED_ENGLISH_MULTI_COLON_RE = re.compile(
    rf"(?<!\S)[A-Za-z][A-Za-z0-9]*-[A-Za-z][A-Za-z0-9-]*\s+{_MULTI_COLON_SURFACE}(?![A-Za-z0-9_/])"
)

_STANDALONE_PATTERNS = tuple(
    re.compile(rf"^{pattern}$")
    for pattern in (
        rf"{_SIGN}{_DECIMAL}{_NUMBER_UNIT_GAP}{_TEMP_UNIT}",
        _CURRENCY_TOKEN,
        _FRACTION,
        _PERCENT_POINT,
        _PERCENT_TOKEN,
        _PH,
        _UNIT_TOKEN,
        _COMPOUND_TOKEN,
        _RANGE,
        _DURATION,
        _TIME,
        _DATE,
        _SPACED_FREQUENCY,
        _PH_SUFFIX_POSITION,
        _SIGNED_NUMBER_TOKEN,
        _DECIMAL_TOKEN,
        _MIDDLE_DOT_TOKEN,
        _TWO_BLOCK_HYPHEN_CODE,
        _INTEGER,
    )
)

_NUMERIC_LIST_TOKEN_RE = re.compile(
    rf"""
    (?:
        {_CURRENCY_TOKEN}
        |{_PERCENT_POINT}
        |{_PERCENT_TOKEN}
        |{_PH}
        |{_FRACTION}
        |{_RANGE}
        |{_DURATION}
        |{_COMPOUND_TOKEN}
        |{_UNIT_TOKEN}
        |{_INTEGER}
    )
    """,
    re.VERBOSE,
)
_CURRENCY_MARKER_LINES = frozenset(
    {
        *CURRENCY_CODE_READINGS.keys(),
        *CURRENCY_SYMBOL_READINGS.keys(),
        *KOREAN_CURRENCY_SUFFIX_READINGS.keys(),
    }
)
_CURRENCY_NUMBER_LINE_RE = re.compile(rf"{_SIGN}{_DECIMAL}")


@dataclass(frozen=True)
class ClassifiedLine:
    text: str
    newline: str
    has_hangul: bool
    is_code_like: bool
    is_standalone: bool
    is_numeric_list: bool


def has_hangul_syllable(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return _HANGUL_SYLLABLE_RE.search(text) is not None


def is_url_email_path_json_shell_line(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.strip()
    if not stripped:
        return False
    if is_standalone_supported_token(stripped):
        return False
    lower = stripped.lower()
    if _URL_WHOLE_RE.fullmatch(stripped):
        return True
    if _EMAIL_RE.fullmatch(stripped):
        return True
    if stripped.startswith("{") and (":" in stripped or '"' in stripped or "'" in stripped):
        return True
    if stripped.startswith("[") and (
        '"' in stripped or "'" in stripped or stripped.startswith("[{")
    ):
        return True
    if lower.startswith(_SHELL_PREFIXES):
        return True
    if is_standalone_protected_literal(stripped):
        return True
    return False


def is_code_like_line(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.strip()
    if not stripped:
        return False
    if is_url_email_path_json_shell_line(stripped):
        return True
    if is_standalone_supported_token(stripped):
        return False
    masked = mask_protected_literals(stripped)
    lower = masked.lower()
    if lower.startswith(_CODE_PREFIXES):
        return True
    if any(marker in masked for marker in ("=>", "==", "!=", "<=", ">=", "&&", "||")):
        return True
    if any(ch in masked for ch in ("{", "}", ";", "=")):
        return True
    return False


def is_standalone_supported_token(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.strip()
    if not stripped:
        return False
    return any(pattern.fullmatch(stripped) for pattern in _STANDALONE_PATTERNS)


def is_numeric_list_line(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.strip()
    if not stripped:
        return False
    if is_code_like_line(stripped):
        return False
    cursor = 0
    matched_any = False
    while cursor < len(stripped):
        char = stripped[cursor]
        if char.isspace() or char in {",", "，"}:
            cursor += 1
            continue
        match = _NUMERIC_LIST_TOKEN_RE.match(stripped, cursor)
        if match is None:
            return False
        matched_any = True
        cursor = match.end()
    return matched_any


def classify_lines(text: str) -> list[ClassifiedLine]:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    lines: list[ClassifiedLine] = []
    for raw_line in text.splitlines(keepends=True):
        if raw_line.endswith("\r\n"):
            content = raw_line[:-2]
            newline = "\r\n"
        elif raw_line.endswith("\n") or raw_line.endswith("\r"):
            content = raw_line[:-1]
            newline = raw_line[-1]
        else:
            content = raw_line
            newline = ""
        stripped = content.strip()
        lines.append(
            ClassifiedLine(
                text=content,
                newline=newline,
                has_hangul=has_hangul_syllable(content),
                is_code_like=is_code_like_line(content),
                is_standalone=is_standalone_supported_token(stripped),
                is_numeric_list=is_numeric_list_line(content),
            )
        )
    if not lines and text == "":
        lines.append(
            ClassifiedLine(
                text="",
                newline="",
                has_hangul=False,
                is_code_like=False,
                is_standalone=False,
                is_numeric_list=False,
            )
        )
    return lines


def transform_with_language_gate(
    text: str, core_transform: Callable[[str], str]
) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not callable(core_transform):
        raise TypeError("core_transform must be callable")

    stripped = text.strip()
    if stripped and not has_hangul_syllable(text) and is_code_like_line(stripped):
        return text
    if _is_wrapped_standalone_supported_token(stripped):
        return core_transform(text)
    if stripped and is_standalone_supported_token(stripped):
        return core_transform(text)
    if not has_hangul_syllable(text):
        if is_non_korean_prose_line(text):
            if has_hyphenated_english_multi_colon_context(text):
                return core_transform(text)
            return text
        return core_transform(text)

    lines = classify_lines(text)
    non_empty = [line for line in lines if line.text.strip()]
    if non_empty and all(
        line.has_hangul and not line.is_numeric_list and not line.is_code_like
        for line in non_empty
    ):
        return core_transform(text)

    transformed: list[str] = []
    for index, line in enumerate(lines):
        transformed.append(_transform_line(index, lines, core_transform))
    return "".join(transformed)


def _is_wrapped_standalone_supported_token(stripped: str) -> bool:
    if len(stripped) < 3:
        return False
    pairs = {"[": "]", "(": ")"}
    expected_close = pairs.get(stripped[0])
    if expected_close is None or stripped[-1] != expected_close:
        return False
    inner = stripped[1:-1].strip()
    return is_standalone_supported_token(inner) or bool(
        re.fullmatch(r"[+\-−－]?\d+(?:\.\d+)?", inner)
    )


def _transform_line(
    index: int, lines: list[ClassifiedLine], core_transform: Callable[[str], str]
) -> str:
    line = lines[index]
    original = line.text + line.newline
    if not line.text.strip():
        return original
    if _has_split_currency_context(lines, index):
        return original
    if line.is_standalone:
        return core_transform(line.text) + line.newline
    if line.is_numeric_list:
        if _has_adjacent_korean_context(lines, index):
            return core_transform(line.text) + line.newline
        return original
    if line.has_hangul:
        return core_transform(line.text) + line.newline
    if line.is_code_like:
        return original
    return original


def _has_adjacent_korean_context(lines: list[ClassifiedLine], index: int) -> bool:
    for neighbor_index in (index - 1, index + 1):
        if neighbor_index < 0 or neighbor_index >= len(lines):
            continue
        neighbor = lines[neighbor_index]
        if not neighbor.text.strip():
            continue
        if neighbor.is_code_like or neighbor.is_numeric_list:
            continue
        if neighbor.has_hangul:
            return True
    return False


def _has_split_currency_context(lines: list[ClassifiedLine], index: int) -> bool:
    stripped = lines[index].text.strip()
    if not _CURRENCY_NUMBER_LINE_RE.fullmatch(stripped):
        return False
    for neighbor_index in (index - 1, index + 1):
        if neighbor_index < 0 or neighbor_index >= len(lines):
            continue
        if lines[neighbor_index].text.strip() in _CURRENCY_MARKER_LINES:
            return True
    return False


def is_non_korean_prose_line(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    stripped = text.strip()
    if not stripped:
        return False
    if is_code_like_line(stripped) or is_standalone_supported_token(stripped):
        return False
    if " " not in stripped:
        return False
    masked = mask_protected_literals(stripped)
    lowercase_words = re.findall(r"\b[A-Za-z]*[a-z][A-Za-z]*\b", masked)
    if not lowercase_words:
        return False
    return any(len(word) >= 3 for word in lowercase_words)


def has_hyphenated_english_multi_colon_context(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return _HYPHENATED_ENGLISH_MULTI_COLON_RE.search(text.strip()) is not None


__all__ = [
    "ClassifiedLine",
    "classify_lines",
    "has_hyphenated_english_multi_colon_context",
    "has_hangul_syllable",
    "is_code_like_line",
    "is_numeric_list_line",
    "is_non_korean_prose_line",
    "is_standalone_supported_token",
    "is_url_email_path_json_shell_line",
    "transform_with_language_gate",
]
