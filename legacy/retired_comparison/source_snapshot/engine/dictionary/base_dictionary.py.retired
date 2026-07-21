from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class DictionaryEntry:
    surface: str
    reading: str
    allow_josa: bool = True
    source_section: str = ""


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PRODUCTION_FILES = (
    _DATA_DIR / "dictionary.base.production.json",
    _DATA_DIR / "dictionary.extended.production.json",
)

# USER.md: 1-3 조사 결합 원칙
_JOSA_SUFFIXES = tuple(
    sorted(
        [
            "으로",
            "에서",
            "에게",
            "한테",
            "이랑",
            "까지",
            "부터",
            "이란",
            "에는",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "와",
            "과",
            "의",
            "에",
            "로",
            "만",
            "도",
            "란",
            "뿐",
            "고",
        ],
        key=len,
        reverse=True,
    )
)
_JOSA_PATTERN = "(?:" + "|".join(map(re.escape, _JOSA_SUFFIXES)) + ")"
_BOUNDARY_CLASS = r"A-Za-z0-9가-힣"


# USER.md: 3-5-4 대문자 약어 fallback.
# Add new USER.md dictionary entries here before relying on fallback behavior.
_UPPER_ABBR_KO = {
    "A": "에이",
    "B": "비",
    "C": "씨",
    "D": "디",
    "E": "이",
    "F": "에프",
    "G": "지",
    "H": "에이치",
    "I": "아이",
    "J": "제이",
    "K": "케이",
    "L": "엘",
    "M": "엠",
    "N": "엔",
    "O": "오",
    "P": "피",
    "Q": "큐",
    "R": "알",
    "S": "에스",
    "T": "티",
    "U": "유",
    "V": "브이",
    "W": "더블유",
    "X": "엑스",
    "Y": "와이",
    "Z": "지",
}
_AMBIGUOUS_UPPER_FALLBACKS = {
    "AIM",
}
_STANDALONE_UPPER_UNIT_EXCLUSIONS = frozenset({"KB", "MB", "GB", "TB", "PB"})
_EMERGENCY_NUMBER_SURFACES = frozenset({"112", "119"})

# USER.md: 7-3 숫자 읽기 표.
_DIGIT_KO = {
    "0": "영",
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
_SMALL_UNITS = ["", "십", "백", "천"]
_LARGE_UNITS = ["", "만", "억", "조", "경", "해"]
_NATIVE_HOUR_KO = {
    1: "한",
    2: "두",
    3: "세",
    4: "네",
    5: "다섯",
    6: "여섯",
    7: "일곱",
    8: "여덟",
    9: "아홉",
    10: "열",
    11: "열한",
    12: "열두",
}

# USER.md: 2-15 전화번호 숫자 읽기.
_PHONE_DIGIT_KO = {
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

# USER.md: 7-7 단위 전체 표
_BASIC_UNITS = {
    "km": "킬로미터",
    "m": "미터",
    "cm": "센티미터",
    "mm": "밀리미터",
    "kg": "킬로그램",
    "g": "그램",
    "mg": "밀리그램",
    "㎡": "제곱미터",
    "m²": "제곱미터",
    "㎥": "세제곱미터",
    "m³": "세제곱미터",
    "L": "리터",
    "mL": "밀리리터",
    "km/h": "킬로미터 퍼 아워",
    "m/s": "미터 퍼 세컨드",
    "km/L": "킬로미터 퍼 리터",
    "GB/s": "기가바이트 퍼 세컨드",
    "W": "와트",
    "kW": "킬로와트",
    "MW": "메가와트",
    "Wh": "와트시",
    "kWh": "킬로와트시",
    "MWh": "메가와트시",
    "MHz": "메가헤르츠",
    "GHz": "기가헤르츠",
    "도": "도",
}
_FILESIZE_UNITS = {
    "KB": "킬로바이트",
    "MB": "메가바이트",
    "GB": "기가바이트",
    "TB": "테라바이트",
}


# USER.md: 3-2-1 영문 약어 사전
# Add new USER.md dictionary entries here.
_SECTION_3_2_1_ENTRIES = (
    DictionaryEntry("AI", "에이아이", source_section="3-2-1. 영문 약어 사전"),
    DictionaryEntry("KBS", "케이비에스", source_section="3-2-1. 영문 약어 사전"),
    DictionaryEntry("WHO", "더블유에이치오", source_section="3-2-1. 영문 약어 사전"),
    DictionaryEntry("iPhone", "아이폰", source_section="3-2-1. 영문 약어 사전"),
    DictionaryEntry("Samsung", "삼성", source_section="3-2-1. 영문 약어 사전"),
    DictionaryEntry("USB", "유에스비", source_section="3-2-1. 영문 약어 사전"),
)

# USER.md: 3-2-2 고정 제품/기술 표기 사전
_SECTION_3_2_2_ENTRIES = (
    DictionaryEntry("4K", "포케이", source_section="3-2-2. 고정 제품/기술 표기 사전"),
    DictionaryEntry("USB 3.0", "유에스비 삼쩜영", allow_josa=False, source_section="3-2-2. 고정 제품/기술 표기 사전"),
)

# USER.md: 3-2-3 기관/지수명 사전
_SECTION_3_2_3_ENTRIES = (
    DictionaryEntry("KOSPI", "코스피", source_section="3-2-3. 기관/지수명 사전"),
    DictionaryEntry("KOSDAQ", "코스닥", source_section="3-2-3. 기관/지수명 사전"),
)

# USER.md: 3-2-4 사건명 표기 사전
_SECTION_3_2_4_ENTRIES = (
    DictionaryEntry("5·18 민주화운동", "오일팔 민주화운동", source_section="3-2-4. 사건명 표기 사전"),
    DictionaryEntry("5·18 민주화 운동", "오일팔 민주화 운동", source_section="3-2-4. 사건명 표기 사전"),
    DictionaryEntry("4·19 혁명", "사일구 혁명", source_section="3-2-4. 사건명 표기 사전"),
    DictionaryEntry("12.12 사태", "십이십이 사태", source_section="3-2-4. 사건명 표기 사전"),
)

# USER.md: 3-5-3-1 국제기구 / 정부기관
_SECTION_3_5_3_1_ENTRIES = (
    DictionaryEntry("UN", "유엔", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("IMF", "아이엠에프", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("WTO", "더블유티오", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("OECD", "오이씨디", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("NATO", "나토", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("NASA", "나사", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("UNESCO", "유네스코", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("UNICEF", "유니세프", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("IAEA", "아이에이이에이", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("ILO", "아이엘오", source_section="3-5-3-1. 국제기구 / 정부기관"),
    DictionaryEntry("FAO", "에프에이오", source_section="3-5-3-1. 국제기구 / 정부기관"),
)

# USER.md: 3-5-3-2 IT / 기술 용어
# Expanded entries here are for terms whose natural live reading should beat
# the generic compact acronym fallback when a curated dictionary reading exists.
_SECTION_3_5_3_2_ENTRIES = (
    DictionaryEntry("API", "에이피아이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("CPU", "씨피유", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("DB", "디비", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("DNS", "디엔에스", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("FAQ", "에프에이큐", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("GPU", "지피유", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("GUI", "지유아이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("HTTP", "에이치티티피", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("HTTPS", "에이치티티피에스", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("IDE", "아이디이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("IoT", "아이오티", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("UI", "유아이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("URL", "유알엘", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("UX", "유엑스", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("IP", "아이피", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("OS", "오에스", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("RAM", "램", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("ROM", "롬", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("SDK", "에스디케이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("TCP", "티씨피", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("UDP", "유디피", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("UX/UI", "유엑스 유아이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("UI/UX", "유아이 유엑스", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("CSV", "씨에스브이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("CV", "씨브이", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("DL", "디엘", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("GAN", "간", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("JSON", "제이슨", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("ML", "엠엘", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("NLP", "엔엘피", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("RL", "알엘", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("SQL", "에스큐엘", source_section="3-5-3-2. IT / 기술 용어"),
    DictionaryEntry("XML", "엑스엠엘", source_section="3-5-3-2. IT / 기술 용어"),
)

# USER.md: 3-5-3-3 통신 / 네트워크
_SECTION_3_5_3_3_ENTRIES = (
    DictionaryEntry("LTE", "엘티이", source_section="3-5-3-3. 통신 / 네트워크"),
    DictionaryEntry("5G", "파이브지", source_section="3-5-3-3. 통신 / 네트워크"),
    DictionaryEntry("4G", "포지", source_section="3-5-3-3. 통신 / 네트워크"),
    DictionaryEntry("WiFi", "와이파이", source_section="3-5-3-3. 통신 / 네트워크"),
    DictionaryEntry("Wi-Fi", "와이파이", source_section="3-5-3-3. 통신 / 네트워크"),
    DictionaryEntry("Bluetooth", "블루투스", source_section="3-5-3-3. 통신 / 네트워크"),
)

# USER.md: 3-5-3-4 과학 / 기술
_SECTION_3_5_3_4_ENTRIES = (
    DictionaryEntry("DNA", "디엔에이", source_section="3-5-3-4. 과학 / 기술"),
    DictionaryEntry("RNA", "알엔에이", source_section="3-5-3-4. 과학 / 기술"),
    DictionaryEntry("UV", "유브이", source_section="3-5-3-4. 과학 / 기술"),
    DictionaryEntry("IR", "아이알", source_section="3-5-3-4. 과학 / 기술"),
    DictionaryEntry("LED", "엘이디", source_section="3-5-3-4. 과학 / 기술"),
    DictionaryEntry("LCD", "엘씨디", source_section="3-5-3-4. 과학 / 기술"),
    DictionaryEntry("OLED", "오엘이디", source_section="3-5-3-4. 과학 / 기술"),
)

# USER.md: 3-5-3-5 경제 / 금융
_SECTION_3_5_3_5_ENTRIES = (
    DictionaryEntry("B2B", "비투비", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("B2C", "비투씨", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("CPI", "씨피아이", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("GDP", "지디피", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("GNP", "지엔피", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("KPI", "케이피아이", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("NASDAQ", "나스닥", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("PPI", "피피아이", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("ROI", "알오아이", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("S&P500", "에스엔피 오백", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("SNP500", "에스엔피 오백", source_section="3-5-3-5. 경제 / 금융"),
    DictionaryEntry("EBITDA", "이비트다", source_section="3-5-3-5. 경제 / 금융"),
)

# USER.md: 3-5-3-6 방송 / 미디어
_SECTION_3_5_3_6_ENTRIES = (
    DictionaryEntry("BBC", "비비씨", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("CNN", "씨엔엔", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("JTBC", "제이티비씨", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("MBC", "엠비씨", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("OTT", "오티티", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("RNN", "알엔엔", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("SBS", "에스비에스", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("SNS", "에스엔에스", source_section="3-5-3-6. 방송 / 미디어"),
    DictionaryEntry("VOD", "브이오디", source_section="3-5-3-6. 방송 / 미디어"),
)

# USER.md: 3-5-3-7 파일 / 확장자
_SECTION_3_5_3_7_ENTRIES = (
    DictionaryEntry("PDF", "피디에프", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("JPG", "제이피지", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("PNG", "피엔지", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("MP3", "엠피쓰리", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("MP4", "엠피포", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("ZIP", "집", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("EXE", "이엑스이", source_section="3-5-3-7. 파일 / 확장자"),
    DictionaryEntry("QR", "큐알", source_section="3-5-3-7. 파일 / 확장자"),
)

# USER.md: 3-5-4 대문자 약어 fallback 예외
_SECTION_3_5_4_EXCEPTION_ENTRIES = (
    DictionaryEntry("IaaS", "이아스", source_section="3-5-4. 조건 기반 확장 규칙"),
    DictionaryEntry("OK", "오케이", source_section="3-5-4. 조건 기반 확장 규칙"),
    DictionaryEntry("ID", "아이디", source_section="3-5-4. 조건 기반 확장 규칙"),
    DictionaryEntry("PaaS", "파스", source_section="3-5-4. 조건 기반 확장 규칙"),
    DictionaryEntry("SaaS", "사스", source_section="3-5-4. 조건 기반 확장 규칙"),
    DictionaryEntry("TV", "티비", source_section="3-5-4. 조건 기반 확장 규칙"),
)

_USER_DICTIONARY_SECTIONS = (
    _SECTION_3_2_1_ENTRIES,
    _SECTION_3_2_2_ENTRIES,
    _SECTION_3_2_3_ENTRIES,
    _SECTION_3_2_4_ENTRIES,
    _SECTION_3_5_3_1_ENTRIES,
    _SECTION_3_5_3_2_ENTRIES,
    _SECTION_3_5_3_3_ENTRIES,
    _SECTION_3_5_3_4_ENTRIES,
    _SECTION_3_5_3_5_ENTRIES,
    _SECTION_3_5_3_6_ENTRIES,
    _SECTION_3_5_3_7_ENTRIES,
    _SECTION_3_5_4_EXCEPTION_ENTRIES,
)


def _load_production_dictionary() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in _PRODUCTION_FILES:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        merged.update(data)
    for surface in _EMERGENCY_NUMBER_SURFACES:
        merged.pop(surface, None)
    return merged


def _build_user_entries() -> dict[str, DictionaryEntry]:
    entries: dict[str, DictionaryEntry] = {}
    for section_entries in _USER_DICTIONARY_SECTIONS:
        for entry in section_entries:
            entries[entry.surface] = entry
    return entries


@lru_cache(maxsize=1)
def load_dictionary_entries() -> dict[str, DictionaryEntry]:
    entries = _build_user_entries()
    for surface, reading in _load_production_dictionary().items():
        entries.setdefault(surface, DictionaryEntry(surface, reading, source_section="production dictionary"))
    return entries


@lru_cache(maxsize=1)
def load_dictionary() -> dict[str, str]:
    return {surface: entry.reading for surface, entry in load_dictionary_entries().items()}


def _split_josa(text: str) -> tuple[str, str] | None:
    for suffix in _JOSA_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[: -len(suffix)], suffix
    return None


def _should_read_upper_fallback(text: str) -> bool:
    if not re.fullmatch(r"[A-Z]+", text):
        return False

    if text in _AMBIGUOUS_UPPER_FALLBACKS:
        return False

    return True


def _read_upper_abbreviation(text: str) -> str | None:
    if not _should_read_upper_fallback(text):
        return None
    if text in _STANDALONE_UPPER_UNIT_EXCLUSIONS:
        return None
    return "".join(_UPPER_ABBR_KO[char] for char in text)


def _compile_surface_pattern(entries: dict[str, DictionaryEntry]) -> re.Pattern[str]:
    exact_only = sorted(
        (re.escape(surface) for surface, entry in entries.items() if not entry.allow_josa),
        key=len,
        reverse=True,
    )
    allow_josa = sorted(
        (re.escape(surface) for surface, entry in entries.items() if entry.allow_josa),
        key=len,
        reverse=True,
    )

    parts: list[str] = []
    if exact_only:
        parts.append(
            rf"(?<![{_BOUNDARY_CLASS}])(?:{'|'.join(exact_only)})(?=$|[^{_BOUNDARY_CLASS}])"
        )
    if allow_josa:
        parts.append(
            rf"(?<![{_BOUNDARY_CLASS}])(?:{'|'.join(allow_josa)})(?=(?:{_JOSA_PATTERN})(?![{_BOUNDARY_CLASS}])|$|[^{_BOUNDARY_CLASS}])"
        )

    if not parts:
        return re.compile(r"(?!x)x")
    return re.compile("|".join(parts))


@lru_cache(maxsize=1)
def _dictionary_surface_pattern() -> re.Pattern[str]:
    return _compile_surface_pattern(load_dictionary_entries())


def _match_exact_dictionary(text: str, dictionary: dict[str, DictionaryEntry]) -> str | None:
    if text in _STANDALONE_UPPER_UNIT_EXCLUSIONS:
        return None
    entry = dictionary.get(text)
    if entry is not None:
        return entry.reading
    return None


def _is_adjacent_to_slash(text: str, start: int, end: int) -> bool:
    left = start - 1
    while left >= 0 and text[left].isspace():
        left -= 1

    right = end
    while right < len(text) and text[right].isspace():
        right += 1

    return (left >= 0 and text[left] == "/") or (right < len(text) and text[right] == "/")


def match_dictionary(text: str) -> str | None:
    # USER.md: 3-1, 3-2, 3-3, 3-5-4
    dictionary = load_dictionary_entries()

    exact = _match_exact_dictionary(text, dictionary)
    if exact is not None:
        return exact

    split = _split_josa(text)
    if split is not None:
        stem, suffix = split
        stem_entry = dictionary.get(stem)
        if stem_entry is not None and stem_entry.allow_josa:
            return f"{stem_entry.reading}{suffix}"

        stem_match = _read_upper_abbreviation(stem)
        if stem_match is not None:
            return f"{stem_match}{suffix}"

    return _read_upper_abbreviation(text)


def apply_dictionary(text: str) -> str:
    # USER.md: 1-2 문자 경계, 1-3 조사 결합, 3-5-6 longest match 우선
    dictionary = load_dictionary_entries()
    pattern = _dictionary_surface_pattern()

    def _replace(match: re.Match[str]) -> str:
        surface = match.group(0)
        if _is_adjacent_to_slash(text, match.start(), match.end()):
            return surface
        entry = dictionary.get(surface)
        if entry is not None:
            return entry.reading
        return surface

    replaced = pattern.sub(_replace, text)

    def _replace_upper(match: re.Match[str]) -> str:
        original = match.group(0)
        if _is_adjacent_to_slash(replaced, match.start(), match.end()):
            return original
        replaced_text = match_dictionary(original)
        if replaced_text is None:
            return original
        return replaced_text

    upper_pattern = re.compile(
        rf"(?<![{_BOUNDARY_CLASS}])[A-Z]+(?=(?:{_JOSA_PATTERN})(?![{_BOUNDARY_CLASS}])|$|[^{_BOUNDARY_CLASS}])"
    )
    return upper_pattern.sub(_replace_upper, replaced)


DIGIT_KO = _DIGIT_KO
SMALL_UNITS = _SMALL_UNITS
LARGE_UNITS = _LARGE_UNITS
NATIVE_HOUR_KO = _NATIVE_HOUR_KO
PHONE_DIGIT_KO = _PHONE_DIGIT_KO
BASIC_UNITS = _BASIC_UNITS
FILESIZE_UNITS = _FILESIZE_UNITS
