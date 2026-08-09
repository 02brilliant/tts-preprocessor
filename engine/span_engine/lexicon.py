from __future__ import annotations

from engine.span_engine.numeric_reading import read_spaced_integer_text
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate

DICTIONARY_READINGS: dict[str, str] = {
    "AFC": "에이에프씨",
    "ASEAN": "아세안",
    "ASR": "에이에스알",
    "B2B": "비투비",
    "B2B/B2C": "비투비 비투씨",
    "B2C": "비투씨",
    "BOJ": "비오제이",
    "BOK": "비오케이",
    "BPS": "비피에스",
    "CSS": "씨에스에스",
    "CSV": "씨에스브이",
    "CLI": "씨엘아이",
    "DB": "디비",
    "DBMS": "디비엠에스",
    "DOC": "디오씨",
    "DOW": "다우",
    "FTA": "에프티에이",
    "FAQ": "에프에이큐",
    "FA": "에프에이",
    "FOMC": "에프오엠씨",
    "Fed": "연준",
    "GDP": "지디피",
    "GPT": "지피티",
    "GraphQL": "그래프큐엘",
    "GUI": "지유아이",
    "HTTP": "에이치티티피",
    "HTTPS": "에이치티티피에스",
    "HWP": "에이치더블유피",
    "IAEA": "아이에이이에이",
    "IDE": "아이디이",
    "MFN": "엠에프엔",
    "HTML": "에이치티엠엘",
    "IMF": "아이엠에프",
    "IOC": "아이오씨",
    "IPTV": "아이피티비",
    "JS": "제이에스",
    "JWT": "제이더블유티",
    "KBL": "케이비엘",
    "KBO": "케이비오",
    "KFA": "케이에프에이",
    "KOSPI": "코스피",
    "KOSDAQ": "코스닥",
    "KTX": "케이티엑스",
    "LAN": "랜",
    "MLB": "엠엘비",
    "NASA": "나사",
    "NASDAQ": "나스닥",
    "NBA": "엔비에이",
    "NFC": "엔에프씨",
    "NFL": "엔에프엘",
    "NHL": "엔에이치엘",
    "NATO": "나토",
    "NLP": "엔엘피",
    "NoSQL": "노에스큐엘",
    "OAuth": "오어스",
    "OpenAI": "오픈 에이아이",
    "OPEC": "오펙",
    "OS": "오에스",
    "PPI": "피피아이",
    "PCIe": "피씨아이이",
    "PPT": "피피티",
    "RAM": "램",
    "release": "릴리즈",
    "REST": "레스트",
    "ROM": "롬",
    "TTS": "티티에스",
    "STT": "에스티티",
    "API": "에이피아이",
    "CPI": "씨피아이",
    "GPU": "지피유",
    "UI": "유아이",
    "UI/UX": "유아이 유엑스",
    "UX/UI": "유엑스 유아이",
    "UX": "유엑스",
    "PDF": "피디에프",
    "JSON": "제이슨",
    "URL": "유알엘",
    "URI": "유알아이",
    "XML": "엑스엠엘",
    "YAML": "야믈",
    "2G": "투지",
    "3G": "쓰리지",
    "3G/4G/5G": "쓰리지/포지/파이브지",
    "K-POP": "케이팝",
    "4K": "포케이",
    "4G": "포지",
    "5G": "파이브지",
    "6G": "식스지",
    "8K": "에잇케이",
    "KBS": "케이비에스",
    "MBC": "엠비씨",
    "M-SAM": "엠-샘",
    "MQ": "엠큐",
    "SBS": "에스비에스",
    "EBS": "이비에스",
    "JTBC": "제이티비씨",
    "OTT": "오티티",
    "VOD": "브이오디",
    "LLM": "엘엘엠",
    "OECD": "오이씨디",
    "WHO": "더블유에이치오",
    "UN": "유엔",
    "UNESCO": "유네스코",
    "UNICEF": "유니세프",
    "WTO": "더블유티오",
    "WAN": "더블유에이엔",
    "WIFI": "와이파이",
    "WLAN": "더블유랜",
    "HD": "에이치디",
    "FHD": "에프에이치디",
    "UHD": "유에이치디",
    "HDR": "에이치디알",
    "SDR": "에스디알",
    "SQL": "에스큐엘",
    "SSL": "에스에스엘",
    "SSH": "에스에스에이치",
    "TLS": "티엘에스",
    "TCP": "티씨피",
    "UDP": "유디피",
    "UWB": "유더블유비",
    "DOCX": "디오씨엑스",
    "XLSX": "엑스엘에스엑스",
    "XLS": "엑스엘에스",
    "PPTX": "피피티엑스",
    "TXT": "티엑스티",
    "TSV": "티에스브이",
    "NPU": "엔피유",
    "SSD": "에스에스디",
    "HDD": "에이치디디",
    "HDMI": "에이치디엠아이",
    "LTE": "엘티이",
    "L-SAM": "엘-샘",
    "IP": "아이피",
    "DNS": "디엔에스",
    "VPN": "브이피엔",
    "WiFi": "와이파이",
    "Wi-Fi": "와이파이",
    "YoY": "와이오와이",
    "MoM": "엠오엠",
    "QoQ": "큐오큐",
    "gRPC": "지알피씨",
    "FAO": "에프에이오",
    "FIFA": "피파",
    "ECB": "이씨비",
    "ETF": "이티에프",
    "ETN": "이티엔",
    "IPO": "아이피오",
    "ROE": "알오이",
    "PER": "피이알",
    "PBR": "피비알",
    "EPS": "이피에스",
    "SDK": "에스디케이",
    "version": "버전",
}

LEXICAL_COMPOUND_READINGS: dict[str, str] = {
    "ISO·IEC": "아이에스오·아이이씨",
}
FINANCE_INDEX_BASE_READINGS: dict[str, str] = {
    "S&P": "에스앤피",
    "NASDAQ": "나스닥",
    "KOSPI": "코스피",
    "KOSDAQ": "코스닥",
}
CONTEXTUAL_ACRONYM_READINGS: dict[str, str] = {
    "KB": "케이비",
}
CASE_INSENSITIVE_NUMERIC_CODE_READINGS: dict[str, str] = {
    "F/A": "에프에이",
    "A/S": "에이에스",
    "Mig": "미그",
    "Su": "수호이",
    "MK": "엠케이",
    "KC": "케이씨",
    "AIM": "에이아이엠",
    "AGM": "에이지엠",
}
_K_HANGUL_PREFIX = "K-"
_K_HANGUL_UNSAFE_TAIL_CHARS = frozenset("-_/.")

LETTER_READINGS: dict[str, str] = {
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


def dictionary_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return DICTIONARY_READINGS.get(raw)


def contextual_acronym_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return CONTEXTUAL_ACRONYM_READINGS.get(raw)


def lexical_compound_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return LEXICAL_COMPOUND_READINGS.get(raw)


def parse_finance_index_numeric_suffix_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "finance_index":
        return None
    reading = candidate.metadata.get("reading")
    return reading if isinstance(reading, str) else None


def k_hangul_lexical_reading(raw: str) -> str | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    if not raw.startswith(_K_HANGUL_PREFIX):
        return None
    hangul = raw[len(_K_HANGUL_PREFIX) :]
    if not hangul or not all(_is_complete_hangul(char) for char in hangul):
        return None
    return f"케이{hangul}"


def spell_uppercase_acronym(raw: str) -> str:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return "".join(LETTER_READINGS[char] for char in raw)


def scan_contextual_acronym_candidates(
    raw_text: str,
    unit_candidates: list[SurfaceCandidate],
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(unit_candidates, list):
        raise TypeError("unit_candidates must be list[SurfaceCandidate]")
    candidates: list[SurfaceCandidate] = []
    for surface in CONTEXTUAL_ACRONYM_READINGS:
        start = raw_text.find(surface)
        while start != -1:
            end = start + len(surface)
            span = SourceSpan(start, end)
            if (
                _safe_contextual_acronym_boundary(raw_text, start, end)
                and not any(
                    _spans_overlap(span, unit_candidate.full_span)
                    for unit_candidate in unit_candidates
                )
            ):
                candidates.append(
                    SurfaceCandidate(
                        core_span=span,
                        full_span=span,
                        owner="contextual_acronym",
                        surface_type="CONTEXTUAL_ACRONYM_SURFACE",
                        reason="approved_dual_role_acronym_outside_unit_context",
                    )
                )
            start = raw_text.find(surface, start + 1)
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def scan_ampersand_acronym_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_upper(raw_text[index]):
            index += 1
            continue
        left_start = index
        while index < len(raw_text) and _is_ascii_upper(raw_text[index]):
            index += 1
        left_end = index
        if index >= len(raw_text) or raw_text[index] != "&":
            continue
        ampersand_start = index
        index += 1
        right_start = index
        while index < len(raw_text) and _is_ascii_upper(raw_text[index]):
            index += 1
        right_end = index
        if right_start == right_end:
            continue
        if not _safe_ampersand_acronym_boundary(raw_text, left_start, right_end):
            continue
        left = raw_text[left_start:left_end]
        right = raw_text[right_start:right_end]
        span = SourceSpan(left_start, right_end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="ampersand_acronym",
                surface_type="AMPERSAND_ACRONYM_SURFACE",
                reason="safe_uppercase_ampersand_acronym_full_claim",
                metadata={
                    "left_reading": spell_uppercase_acronym(left),
                    "right_reading": spell_uppercase_acronym(right),
                    "left_span": SourceSpan(left_start, left_end),
                    "ampersand_span": SourceSpan(
                        ampersand_start, ampersand_start + 1
                    ),
                    "right_span": SourceSpan(right_start, right_end),
                },
            )
        )
    return candidates


def scan_unsupported_ampersand_acronym_preserve_candidates(
    raw_text: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (raw_text[index].isascii() and raw_text[index].isalnum()):
            index += 1
            continue
        start = index
        while index < len(raw_text) and (
            (raw_text[index].isascii() and raw_text[index].isalnum())
            or raw_text[index] in {"_", "&"}
        ):
            index += 1
        token = raw_text[start:index]
        if "&" not in token or token.startswith("&") or token.endswith("&"):
            continue
        if token.count("&") == 1:
            left, right = token.split("&", 1)
            if (
                left
                and right
                and all(_is_ascii_upper(char) for char in left)
                and all(_is_ascii_upper(char) for char in right)
            ):
                continue
        span = SourceSpan(start, index)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="UNSUPPORTED_AMPERSAND_ACRONYM_PRESERVE_SURFACE",
                reason="unsupported_ampersand_acronym_atomic_preserve",
                metadata={"claim_type": "preserve"},
            )
        )
    return candidates


def parse_ampersand_acronym_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "ampersand_acronym":
        return None
    left_reading = candidate.metadata.get("left_reading")
    right_reading = candidate.metadata.get("right_reading")
    left_span = candidate.metadata.get("left_span")
    ampersand_span = candidate.metadata.get("ampersand_span")
    right_span = candidate.metadata.get("right_span")
    if not (
        isinstance(left_reading, str)
        and isinstance(right_reading, str)
        and isinstance(left_span, SourceSpan)
        and isinstance(ampersand_span, SourceSpan)
        and isinstance(right_span, SourceSpan)
    ):
        return None
    reading = f"{left_reading}앤{right_reading}"
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    render_pieces = [
        RenderPiece(
            text=LETTER_READINGS[raw_text[index]],
            provenance="GENERATED_READING",
            source_span=SourceSpan(index, index + 1),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
        for index in range(left_span.start, left_span.end)
    ]
    render_pieces.append(
        RenderPiece(
            text="앤",
            provenance="GENERATED_READING",
            source_span=ampersand_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
    )
    render_pieces.extend(
        RenderPiece(
            text=LETTER_READINGS[raw_text[index]],
            provenance="GENERATED_READING",
            source_span=SourceSpan(index, index + 1),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
        for index in range(right_span.start, right_span.end)
    )
    return Surface(
        surface_type=candidate.surface_type or "AMPERSAND_ACRONYM_SURFACE",
        owner=candidate.owner,
        raw=raw,
        span=candidate.core_span,
        reading=reading,
        render_pieces=render_pieces,
        metadata={"reason": candidate.reason},
    )


def scan_lexical_compound_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for surface, reading in LEXICAL_COMPOUND_READINGS.items():
        start = raw_text.find(surface)
        while start != -1:
            end = start + len(surface)
            if _safe_fixed_surface_boundary(raw_text, start, end):
                span = SourceSpan(start, end)
                candidates.append(
                    SurfaceCandidate(
                        core_span=span,
                        full_span=span,
                        owner="lexical_compound",
                        surface_type="LEXICAL_COMPOUND_SURFACE",
                        reason="fixed_lexical_compound_match",
                        metadata={"reading": reading},
                    )
                )
            start = raw_text.find(surface, start + 1)
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def scan_acronym_hangul_hyphen_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _is_ascii_upper(raw_text[index]):
            index += 1
            continue
        left_start = index
        while index < len(raw_text) and _is_ascii_upper(raw_text[index]):
            index += 1
        left = raw_text[left_start:index]
        if (
            index >= len(raw_text)
            or raw_text[index] != "-"
            or index + 1 >= len(raw_text)
            or not _is_complete_hangul(raw_text[index + 1])
        ):
            continue
        hangul_start = index + 1
        hangul_end = hangul_start
        while hangul_end < len(raw_text) and _is_complete_hangul(raw_text[hangul_end]):
            hangul_end += 1
        if (
            not _safe_acronym_hangul_left_boundary(raw_text, left_start)
            or not _safe_acronym_hangul_right_boundary(raw_text, hangul_end)
        ):
            continue
        reading = _acronym_hangul_left_reading(left)
        if reading is None:
            continue
        span = SourceSpan(left_start, hangul_end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="acronym_hangul_hyphen",
                surface_type="ACRONYM_HANGUL_HYPHEN_LEXICAL_SURFACE",
                reason="managed_acronym_hangul_hyphen_lexical_compound",
                metadata={
                    "left_reading": reading,
                    "hyphen_span": SourceSpan(index, index + 1),
                    "hangul_span": SourceSpan(hangul_start, hangul_end),
                },
            )
        )
    return candidates


def acronym_hangul_hyphen_render_pieces(
    raw_text: str, candidate: SurfaceCandidate
) -> list[RenderPiece] | None:
    if candidate.owner != "acronym_hangul_hyphen":
        return None
    left_reading = candidate.metadata.get("left_reading")
    hyphen_span = candidate.metadata.get("hyphen_span")
    hangul_span = candidate.metadata.get("hangul_span")
    if (
        not isinstance(left_reading, str)
        or not isinstance(hyphen_span, SourceSpan)
        or not isinstance(hangul_span, SourceSpan)
    ):
        return None
    return [
        RenderPiece(
            text=left_reading,
            provenance="GENERATED_READING",
            source_span=SourceSpan(candidate.core_span.start, hyphen_span.start),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=raw_text[hyphen_span.start : hyphen_span.end],
            provenance="ORIGINAL_BOUNDARY",
            source_span=hyphen_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
        RenderPiece(
            text=raw_text[hangul_span.start : hangul_span.end],
            provenance="ORIGINAL_KOREAN",
            source_span=hangul_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        ),
    ]


def _acronym_hangul_left_reading(left: str) -> str | None:
    fixed = dictionary_reading(left)
    if fixed is not None:
        return fixed
    if len(left) >= 2 and all(_is_ascii_upper(char) for char in left):
        return spell_uppercase_acronym(left)
    return None


def _safe_acronym_hangul_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    prev_char = raw_text[start - 1]
    if prev_char.isspace():
        return True
    return not _is_identifier_neighbor(prev_char)


def _safe_acronym_hangul_right_boundary(raw_text: str, end: int) -> bool:
    if end >= len(raw_text):
        return True
    next_char = raw_text[end]
    if next_char.isascii() and next_char.isalnum():
        return False
    return next_char not in {"_", "-", "/", "."}


def _is_ascii_upper(char: str) -> bool:
    return "A" <= char <= "Z"


def scan_finance_index_numeric_suffix_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    for base, base_reading in sorted(
        FINANCE_INDEX_BASE_READINGS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        start = raw_text.find(base)
        while start != -1:
            number_start = start + len(base)
            if raw_text[number_start : number_start + 1] == " ":
                number_start += 1
            number_end = number_start
            while number_end < len(raw_text) and raw_text[number_end].isdigit():
                number_end += 1
            if number_end > number_start and _safe_finance_index_boundary(raw_text, start, number_end):
                number = raw_text[number_start:number_end]
                number_reading = read_spaced_integer_text(number)
                if number_reading is not None:
                    span = SourceSpan(start, number_end)
                    candidates.append(
                        SurfaceCandidate(
                            core_span=span,
                            full_span=span,
                            owner="finance_index",
                            surface_type="FINANCE_INDEX_NUMERIC_SUFFIX_SURFACE",
                            reason="finance_index_numeric_suffix_full_claim",
                            metadata={"reading": f"{base_reading} {number_reading}"},
                        )
                    )
            start = raw_text.find(base, start + 1)
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def scan_k_hangul_lexical_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    start = raw_text.find(_K_HANGUL_PREFIX)
    while start != -1:
        hangul_start = start + len(_K_HANGUL_PREFIX)
        if not _safe_k_hangul_left_boundary(raw_text, start):
            start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
            continue
        if hangul_start >= len(raw_text) or not _is_complete_hangul(raw_text[hangul_start]):
            start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
            continue
        end = hangul_start
        while end < len(raw_text) and _is_complete_hangul(raw_text[end]):
            end += 1
        if _has_k_hangul_unsafe_tail(raw_text, end):
            start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
            continue
        span = SourceSpan(start, end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="k_hangul_lexical",
                surface_type="K_HANGUL_LEXICAL_SURFACE",
                reason="k_hangul_lexical_prefix_full_consume",
            )
        )
        start = raw_text.find(_K_HANGUL_PREFIX, start + 1)
    return candidates


def _safe_fixed_surface_boundary(raw_text: str, start: int, end: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    if prev_char is not None and _is_identifier_neighbor(prev_char):
        return False
    if next_char is not None and "\uac00" <= next_char <= "\ud7a3":
        return _starts_with_trailing_particle(raw_text, end)
    if next_char is not None and _is_identifier_neighbor(next_char):
        return False
    return True


def _safe_contextual_acronym_boundary(raw_text: str, start: int, end: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    if prev_char is not None and (
        _is_identifier_neighbor(prev_char) or prev_char in {".", "&"}
    ):
        return False
    if next_char is not None and (
        (next_char.isascii() and next_char.isalnum())
        or "\u3130" <= next_char <= "\u318f"
        or next_char in {"_", "-", "/", ".", "&"}
    ):
        return False
    return True


def _safe_ampersand_acronym_boundary(
    raw_text: str, start: int, end: int
) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    if prev_char is not None and (
        (prev_char.isascii() and prev_char.isalnum())
        or "\u3130" <= prev_char <= "\u318f"
        or prev_char in {"_", "-", "/", ".", "&"}
    ):
        return False
    if next_char is not None and (
        (next_char.isascii() and next_char.isalnum())
        or "\u3130" <= next_char <= "\u318f"
        or next_char in {"_", "-", "/", ".", "&"}
    ):
        return False
    return True


def _spans_overlap(left: SourceSpan, right: SourceSpan) -> bool:
    return left.start < right.end and right.start < left.end


def _safe_finance_index_boundary(raw_text: str, start: int, end: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    if prev_char is not None and _is_identifier_neighbor(prev_char):
        return False
    if next_char is not None and _is_unsafe_finance_index_tail(next_char):
        return False
    return True


def _is_unsafe_finance_index_tail(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\u3130" <= char <= "\u318f":
        return True
    return char in {"_", "-", "/", ".", "·", "ㆍ", "∙"}


def _starts_with_trailing_particle(raw_text: str, index: int) -> bool:
    return any(
        raw_text.startswith(particle, index)
        for particle in ("은", "는", "이", "가", "을", "를", "와", "과")
    )


def _safe_k_hangul_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    prev_char = raw_text[start - 1]
    if prev_char.isspace():
        return True
    if _is_identifier_neighbor(prev_char):
        return False
    return True


def _has_k_hangul_unsafe_tail(raw_text: str, end: int) -> bool:
    if end >= len(raw_text):
        return False
    next_char = raw_text[end]
    if next_char.isascii() and next_char.isalnum():
        return True
    return next_char in _K_HANGUL_UNSAFE_TAIL_CHARS


def _is_complete_hangul(char: str) -> bool:
    return "\uac00" <= char <= "\ud7a3"


def _is_identifier_neighbor(char: str) -> bool:
    if char.isascii() and char.isalnum():
        return True
    if "\uac00" <= char <= "\ud7a3" or "\u3130" <= char <= "\u318f":
        return True
    return char in {"-", "_", "/"}


__all__ = [
    "CASE_INSENSITIVE_NUMERIC_CODE_READINGS",
    "CONTEXTUAL_ACRONYM_READINGS",
    "DICTIONARY_READINGS",
    "LETTER_READINGS",
    "LEXICAL_COMPOUND_READINGS",
    "acronym_hangul_hyphen_render_pieces",
    "contextual_acronym_reading",
    "dictionary_reading",
    "k_hangul_lexical_reading",
    "lexical_compound_reading",
    "parse_finance_index_numeric_suffix_candidate",
    "parse_ampersand_acronym_candidate",
    "scan_ampersand_acronym_candidates",
    "scan_unsupported_ampersand_acronym_preserve_candidates",
    "scan_contextual_acronym_candidates",
    "scan_finance_index_numeric_suffix_candidates",
    "scan_acronym_hangul_hyphen_candidates",
    "scan_k_hangul_lexical_candidates",
    "scan_lexical_compound_candidates",
    "spell_uppercase_acronym",
]
