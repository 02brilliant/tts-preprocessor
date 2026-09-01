from __future__ import annotations

from engine.span_engine.amount_reading import read_decimal_amount_text
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_fraction_digits, read_spaced_integer_text
from engine.span_engine.sign_aliases import (
    SIGNED_NUMERIC_SIGN_ALIASES,
    is_signed_numeric_sign,
    strip_signed_numeric_sign,
)
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    apply_sign_profile,
    parse_signed_numeric_core,
    render_signed_numeric,
)
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY

SIMPLE_UNIT_READINGS: dict[str, str] = {
    "THz": "테라헤르츠",
    "Thz": "테라헤르츠",
    "thz": "테라헤르츠",
    "kHz": "킬로헤르츠",
    "KHz": "킬로헤르츠",
    "khz": "킬로헤르츠",
    "MHz": "메가헤르츠",
    "Mhz": "메가헤르츠",
    "mhz": "메가헤르츠",
    "GHz": "기가헤르츠",
    "Ghz": "기가헤르츠",
    "ghz": "기가헤르츠",
    "mL": "밀리리터",
    "ml": "밀리리터",
    "ML": "밀리리터",
    "µL": "마이크로리터",
    "μL": "마이크로리터",
    "uL": "마이크로리터",
    "nL": "나노리터",
    "pL": "피코리터",
    "dL": "데시리터",
    "dl": "데시리터",
    "kL": "킬로리터",
    "kl": "킬로리터",
    "GPa": "기가파스칼",
    "kPa": "킬로파스칼",
    "hPa": "헥토파스칼",
    "mPa": "밀리파스칼",
    "MPa": "메가파스칼",
    "Pa": "파스칼",
    "GWh": "기가와트시",
    "TWh": "테라와트시",
    "mWh": "밀리와트시",
    "MWh": "메가와트시",
    "kWh": "킬로와트시",
    "Wh": "와트시",
    "µW": "마이크로와트",
    "μW": "마이크로와트",
    "uW": "마이크로와트",
    "mW": "밀리와트",
    "MW": "메가와트",
    "kW": "킬로와트",
    "kw": "킬로와트",
    "GW": "기가와트",
    "TW": "테라와트",
    "W": "와트",
    "kV": "킬로볼트",
    "kv": "킬로볼트",
    "µV": "마이크로볼트",
    "μV": "마이크로볼트",
    "uV": "마이크로볼트",
    "nV": "나노볼트",
    "mV": "밀리볼트",
    "MV": "메가볼트",
    "µm": "마이크로미터",
    "μm": "마이크로미터",
    "um": "마이크로미터",
    "nm": "나노미터",
    "mm": "밀리미터",
    "cm": "센티미터",
    "km": "킬로미터",
    "µg": "마이크로그램",
    "μg": "마이크로그램",
    "ug": "마이크로그램",
    "ng": "나노그램",
    "pg": "피코그램",
    "mg": "밀리그램",
    "kg": "킬로그램",
    "Hz": "헤르츠",
    "hz": "헤르츠",
    "mHz": "밀리헤르츠",
    "dB": "데시벨",
    "KB": "킬로바이트",
    "MB": "메가바이트",
    "GB": "기가바이트",
    "TB": "테라바이트",
    "PB": "페타바이트",
    "bits": "비트",
    "bit": "비트",
    "msec": "밀리초",
    "µsec": "마이크로초",
    "μsec": "마이크로초",
    "usec": "마이크로초",
    "nsec": "나노초",
    "secs": "초",
    "sec": "초",
    "Sec": "초",
    "ms": "밀리초",
    "µs": "마이크로초",
    "μs": "마이크로초",
    "us": "마이크로초",
    "ns": "나노초",
    "ps": "피코초",
    "min": "분",
    "ft": "피트",
    "in": "인치",
    "m": "미터",
    "ｍ": "미터",
    "g": "그램",
    "L": "리터",
    "%": "퍼센트",
    "％": "퍼센트",
    "﹪": "퍼센트",
    "bp": "베이시스 포인트",
    "BP": "베이시스 포인트",
}

_NATURAL_CARET_POWER_BASE_READINGS = {
    unit: SIMPLE_UNIT_READINGS[unit] for unit in ("mm", "cm", "km", "m")
}
CARET_POWER_UNIT_READINGS: dict[str, str] = {
    **{
        f"{unit}^2": f"제곱{reading}"
        for unit, reading in _NATURAL_CARET_POWER_BASE_READINGS.items()
    },
    **{
        f"{unit}^3": f"세제곱{reading}"
        for unit, reading in _NATURAL_CARET_POWER_BASE_READINGS.items()
    },
}

SPECIAL_UNIT_READINGS: dict[str, str] = {
    "㎜": "밀리미터",
    "㎝": "센티미터",
    "㎞": "킬로미터",
    "㎛": "마이크로미터",
    "㎚": "나노미터",
    "㎳": "밀리초",
    "㎲": "마이크로초",
    "㎱": "나노초",
    "㎰": "피코초",
    "㎎": "밀리그램",
    "㎏": "킬로그램",
    "㎍": "마이크로그램",
    "㎕": "마이크로리터",
    "㎖": "밀리리터",
    "㎗": "데시리터",
    "㎘": "킬로리터",
    "ℓ": "리터",
    "㎅": "킬로바이트",
    "㎆": "메가바이트",
    "㎇": "기가바이트",
    "㎑": "킬로헤르츠",
    "㎔": "테라헤르츠",
    "㎩": "파스칼",
    "㎪": "킬로파스칼",
    "㎫": "메가파스칼",
    "㎵": "나노볼트",
    "㎶": "마이크로볼트",
    "㎷": "밀리볼트",
    "㎸": "킬로볼트",
    "㎹": "메가볼트",
    "㎼": "마이크로와트",
    "㎽": "밀리와트",
    "㎾": "킬로와트",
    "㎿": "메가와트",
    "㎠": "제곱센티미터",
    "㎢": "제곱킬로미터",
    "㎡": "제곱미터",
    "m²": "제곱미터",
    "m2": "제곱미터",
    "㎟": "제곱밀리미터",
    "mm²": "제곱밀리미터",
    "mm2": "제곱밀리미터",
    "cm²": "제곱센티미터",
    "cm2": "제곱센티미터",
    "km²": "제곱킬로미터",
    "km2": "제곱킬로미터",
    "㎤": "세제곱센티미터",
    "㎦": "세제곱킬로미터",
    "㎥": "세제곱미터",
    "m³": "세제곱미터",
    "m3": "세제곱미터",
    "㎣": "세제곱밀리미터",
    "mm³": "세제곱밀리미터",
    "mm3": "세제곱밀리미터",
    "cm³": "세제곱센티미터",
    "cm3": "세제곱센티미터",
    "km³": "세제곱킬로미터",
    "km3": "세제곱킬로미터",
    "㎐": "헤르츠",
    "㎒": "메가헤르츠",
    "㎓": "기가헤르츠",
    "㏈": "데시벨",
    "‰": "퍼밀",
    "℃": "도",
    "℉": "화씨",
    "º": "도",
    "ºC": "도",
    "ºF": "화씨",
    "°C": "도",
    "°F": "화씨",
    "º C": "도",
    "º F": "화씨",
    "° C": "도",
    "° F": "화씨",
    "°": "도",
}

# N-M range compatibility is opt-in. The current unit registry is a simple
# reading dictionary, so this registry-backed metadata table preserves existing
# approved unit behavior while missing entries default to non-compatible.
RANGE_COMPATIBLE_UNIT_READINGS: dict[str, str] = {
    **SIMPLE_UNIT_READINGS,
    **SPECIAL_UNIT_READINGS,
}

_SIMPLE_UNITS_BY_LENGTH = sorted(SIMPLE_UNIT_READINGS, key=len, reverse=True)
_SPECIAL_UNITS_BY_LENGTH = sorted(SPECIAL_UNIT_READINGS, key=len, reverse=True)
_CARET_POWER_UNITS_BY_LENGTH = sorted(CARET_POWER_UNIT_READINGS, key=len, reverse=True)
_HANGUL_SYLLABLE_START = 0xAC00
_HANGUL_SYLLABLE_END = 0xD7A3
# Hangul-context reading is opt-in per live registered unit. Exclusions are
# single-letter/code-like/template-bound surfaces plus dual-role acronyms
# whose Hangul-adjacent reading is already owned elsewhere.
HANGUL_CONTEXT_UNIT_EXCLUSIONS: frozenset[str] = frozenset(
    {
        "m",
        "ｍ",
        "g",
        "L",
        "W",
        "%",
        "％",
        "﹪",
        "m2",
        "cm2",
        "km2",
        "m3",
        "cm3",
        "km3",
        "℃",
        "℉",
        "º",
        "ºC",
        "ºF",
        "°C",
        "°F",
        "º C",
        "º F",
        "° C",
        "° F",
        "°",
        "KB",
        "ML",
        "MV",
        "in",
        "ft",
        "min",
        "um",
        "ug",
        "pg",
        "us",
        "usec",
        "ps",
        "secs",
        "Sec",
        "mm2",
        "mm3",
        "bp",
        "BP",
    }
)
# English preposition `in` is only safe when the number is attached.
_ATTACHED_NUMERIC_ONLY_UNITS = frozenset({"in"})
# `bit`/`bits` may be read without a number when they are a bare token or
# sit next to Hangul, but not inside English words such as `a bit`.
_STANDALONE_CONTEXT_UNITS = frozenset({"bit", "bits"})
HANGUL_CONTEXT_UNIT_READINGS: dict[str, str] = {
    unit: reading
    for unit, reading in {**SIMPLE_UNIT_READINGS, **SPECIAL_UNIT_READINGS}.items()
    if unit not in HANGUL_CONTEXT_UNIT_EXCLUSIONS
}
_HANGUL_CONTEXT_UNITS_BY_LENGTH = sorted(
    HANGUL_CONTEXT_UNIT_READINGS, key=len, reverse=True
)
_RANGE_COMPATIBLE_UNITS_BY_LENGTH = sorted(
    RANGE_COMPATIBLE_UNIT_READINGS, key=len, reverse=True
)
_PREV_BLOCKERS = frozenset(".,~:/") | SIGNED_NUMERIC_SIGN_ALIASES
_PREV_SYMBOL_BLOCKERS = frozenset("$€£¥₩")
_NEXT_BLOCKERS = frozenset(",~:/") | SIGNED_NUMERIC_SIGN_ALIASES
_SUPERSCRIPT_EXPONENTS = frozenset("²³")
_CJK_COMPATIBILITY_UNIT_SYMBOL_START = ord("㎀")
_CJK_COMPATIBILITY_UNIT_SYMBOL_END = ord("㏟")
_UNSAFE_TAIL_UNITS_BY_LENGTH = sorted(
    {
        *SIMPLE_UNIT_READINGS,
        *SPECIAL_UNIT_READINGS,
        "ºC",
        "ºF",
        "°C",
        "°F",
    },
    key=len,
    reverse=True,
)
_COMPOUND_SLASH_UNIT_SURFACES_BASE = frozenset(
    {
        "km/h",
        "㎞/h",
        "km/hr",
        "km/s",
        "㎞/s",
        "m/min",
        "m/sec",
        "m/s",
        "km/L",
        "km/l",
        "km/ℓ",
        "㎞/L",
        "㎞/l",
        "㎞/ℓ",
        "m/L",
        "m/l",
        "mg/L",
        "㎎/L",
        "g/L",
        "KB/s",
        "Kb/s",
        "kb/s",
        "MB/s",
        "Mb/s",
        "mb/s",
        "GB/s",
        "Gb/s",
        "gb/s",
        "TB/s",
        "Tb/s",
        "tb/s",
        "PB/s",
        "Pb/s",
        "pb/s",
        "mg/dL",
    }
)
_COMPOUND_SLASH_UNIT_SURFACES = frozenset(
    _COMPOUND_SLASH_UNIT_SURFACES_BASE
    | {
        unit.replace("/", "／")
        for unit in _COMPOUND_SLASH_UNIT_SURFACES_BASE
        if "/" in unit
    }
)
_COMPOUND_SLASH_NUMERATOR_PREFIXES = frozenset(
    {
        "km",
        "㎞",
        "m",
        "mg",
        "㎎",
        "g",
        "KB",
        "Kb",
        "kb",
        "MB",
        "KB",
        "Mb",
        "mb",
        "GB",
        "Gb",
        "gb",
        "TB",
        "Tb",
        "tb",
        "PB",
        "Pb",
        "pb",
    }
)
_DATA_RATE_NUMERATOR_PREFIXES = frozenset(
    {"KB", "Kb", "kb", "MB", "Mb", "mb", "GB", "Gb", "gb", "TB", "Tb", "tb", "PB", "Pb", "pb"}
)
_COMPOUND_EXACT_UNIT_SURFACES = frozenset(
    {
        "bps",
        "Kbps",
        "kbps",
        "Mbps",
        "mbps",
        "Gbps",
        "gbps",
        "Tbps",
        "tbps",
        "rpm",
        "fps",
        "ppm",
        "ppb",
        "dBi",
    }
)
_DECIMAL_AMOUNT_UNIT_SURFACES = frozenset(
    {*SIMPLE_UNIT_READINGS, *SPECIAL_UNIT_READINGS}
)
_SPACED_AMOUNT_UNIT_SURFACES = frozenset({"Hz", "hz"})


def scan_caret_power_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    return _scan_unit_candidates(
        raw_text,
        CARET_POWER_UNIT_READINGS,
        _CARET_POWER_UNITS_BY_LENGTH,
        "caret_power_unit",
        "CARET_POWER_UNIT_SURFACE",
    )


def scan_caret_literal_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Read a valid numeric prefix while preserving an unsupported ``unit^N`` block."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (
            _is_ascii_digit(raw_text[index])
            or is_signed_numeric_sign(raw_text[index])
        ):
            index += 1
            continue
        amount_start = index
        numeric_start = (
            amount_start + 1
            if is_signed_numeric_sign(raw_text[amount_start])
            else amount_start
        )
        amount_end = _consume_decimal_number(raw_text, numeric_start)
        if amount_end is None:
            index += 1
            continue
        unit_start = _consume_optional_ascii_space(raw_text, amount_end)
        unit_end = unit_start
        while unit_end < len(raw_text) and (
            raw_text[unit_end].isascii() and raw_text[unit_end].isalpha()
        ):
            unit_end += 1
        if unit_end == unit_start or unit_end >= len(raw_text) or raw_text[unit_end] != "^":
            index += 1
            continue
        exponent_end = unit_end + 1
        while exponent_end < len(raw_text) and (
            raw_text[exponent_end].isascii()
            and raw_text[exponent_end].isalnum()
        ):
            exponent_end += 1
        if exponent_end == unit_end + 1:
            index += 1
            continue
        literal = raw_text[unit_start:exponent_end]
        amount = raw_text[amount_start:amount_end]
        if (
            literal in CARET_POWER_UNIT_READINGS
            and _valid_amount_and_boundary(
                raw_text, SourceSpan(amount_start, exponent_end), amount
            )
            and _valid_caret_power_boundary(raw_text, exponent_end)
        ):
            index = exponent_end
            continue
        core = parse_signed_numeric_core(amount)
        if core is None or not _valid_caret_literal_left_boundary(raw_text, amount_start):
            span = SourceSpan(
                _caret_numeric_like_start(raw_text, amount_start),
                exponent_end,
            )
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner="preserve",
                    surface_type="CARET_LITERAL_PRESERVE_SURFACE",
                    reason="invalid_numeric_caret_literal_preserve",
                )
            )
            index = exponent_end
            continue
        number_reading = render_signed_numeric(core)
        if number_reading is None:
            index += 1
            continue
        span = SourceSpan(amount_start, exponent_end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="caret_literal_unit",
                surface_type="CARET_LITERAL_UNIT_SURFACE",
                reason="unsupported_caret_unit_literal_preserve",
                metadata={
                    "amount_span": SourceSpan(amount_start, amount_end),
                    "gap_span": (
                        SourceSpan(amount_end, unit_start)
                        if unit_start > amount_end
                        else None
                    ),
                    "literal_span": SourceSpan(unit_start, exponent_end),
                    "number_reading": number_reading,
                    "reading": (
                        f"{number_reading}"
                        f"{raw_text[amount_end:unit_start]}"
                        f"{literal}"
                    ),
                },
            )
        )
        index = exponent_end
    candidates.extend(_scan_bare_caret_literal_preserves(raw_text))
    candidates.extend(_scan_spaced_caret_literal_preserves(raw_text))
    return candidates


def parse_caret_literal_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "caret_literal_unit":
        return None
    amount_span = candidate.metadata.get("amount_span")
    gap_span = candidate.metadata.get("gap_span")
    literal_span = candidate.metadata.get("literal_span")
    number_reading = candidate.metadata.get("number_reading")
    if (
        not isinstance(amount_span, SourceSpan)
        or not isinstance(literal_span, SourceSpan)
        or not isinstance(number_reading, str)
        or gap_span is not None
        and not isinstance(gap_span, SourceSpan)
    ):
        return None
    pieces = [
        RenderPiece(
            text=number_reading,
            provenance="GENERATED_READING",
            source_span=amount_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
    ]
    if isinstance(gap_span, SourceSpan):
        pieces.append(
            RenderPiece(
                text=raw_text[gap_span.start : gap_span.end],
                provenance="ORIGINAL_SPACE",
                source_span=gap_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    pieces.append(
        RenderPiece(
            text=raw_text[literal_span.start : literal_span.end],
            provenance="ORIGINAL_BOUNDARY",
            source_span=literal_span,
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
    )
    reading = "".join(piece.text for piece in pieces)
    return Surface(
        surface_type=candidate.surface_type or "CARET_LITERAL_UNIT_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.core_span.start : candidate.core_span.end],
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def scan_simple_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    return _scan_unit_candidates(raw_text, SIMPLE_UNIT_READINGS, _SIMPLE_UNITS_BY_LENGTH, "simple_unit", "SIMPLE_UNIT_SURFACE")


def scan_special_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    return _scan_unit_candidates(raw_text, SPECIAL_UNIT_READINGS, _SPECIAL_UNITS_BY_LENGTH, "special_unit", "SPECIAL_UNIT_SURFACE")


def scan_hangul_context_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Read registered ASCII/symbol units that sit in Hangul prose without a number."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        matched = False
        for unit in _HANGUL_CONTEXT_UNITS_BY_LENGTH:
            if not raw_text.startswith(unit, index):
                continue
            end = index + len(unit)
            if not _valid_hangul_context_unit_boundary(raw_text, index, end):
                continue
            if not _has_hangul_context_neighbor(
                raw_text,
                index,
                end,
                require_left=_requires_left_hangul_context(unit),
            ) and not (
                unit in _STANDALONE_CONTEXT_UNITS
                and _has_standalone_letter_free_context(raw_text, index, end)
            ):
                continue
            unit_reading = HANGUL_CONTEXT_UNIT_READINGS[unit]
            attached_left = index > 0 and _is_hangul_syllable(raw_text[index - 1])
            reading = f" {unit_reading}" if attached_left else unit_reading
            if unit in SPECIAL_UNIT_READINGS:
                owner = "special_unit"
                surface_type = "SPECIAL_UNIT_SURFACE"
            else:
                owner = "simple_unit"
                surface_type = "SIMPLE_UNIT_SURFACE"
            candidates.append(
                SurfaceCandidate(
                    core_span=SourceSpan(index, end),
                    full_span=SourceSpan(index, end),
                    owner=owner,
                    surface_type=surface_type,
                    reason="hangul_context_unit",
                    metadata={
                        "unit": unit,
                        "unit_reading": unit_reading,
                        "reading": reading,
                    },
                )
            )
            index = end
            matched = True
            break
        if not matched:
            index += 1
    return candidates


def scan_korean_numeric_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    """Read registered units after narrowly approved Korean numeric forms."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    # Imported lazily because the large-unit parser itself depends on signed
    # unit detection during module initialization.
    from engine.span_engine.large_unit import (
        parse_large_unit_quantity_core_at,
        parse_mixed_integer_core_at,
    )

    from engine.span_engine.compound_unit import COMPOUND_EXACT_UNIT_NAMES

    inventory = {
        **SIMPLE_UNIT_READINGS,
        **SPECIAL_UNIT_READINGS,
        **COMPOUND_EXACT_UNIT_NAMES,
    }
    ordered_units = sorted(inventory, key=len, reverse=True)
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        at_digit_start = _is_ascii_digit(raw_text[index]) and _valid_korean_numeric_unit_left_boundary(
            raw_text, index
        )
        at_large_start = at_digit_start or (
            is_signed_numeric_sign(raw_text[index])
            and _valid_korean_numeric_unit_left_boundary(raw_text, index)
        )
        parsed = parse_mixed_integer_core_at(raw_text, index) if at_digit_start else None
        if parsed is not None:
            candidate = _korean_numeric_unit_candidate(
                raw_text,
                index,
                parsed.end,
                parsed.reading,
                inventory,
                ordered_units,
                "mixed_arabic_hangul_numeric_unit",
            )
            if candidate is not None:
                candidates.append(candidate)
                index = candidate.full_span.end
                continue

        large_parsed = (
            parse_large_unit_quantity_core_at(raw_text, index) if at_large_start else None
        )
        if large_parsed is not None:
            raw_core = raw_text[index:large_parsed.end]
            split_core = (
                large_parsed.has_decimal
                or large_parsed.has_sign
                or ("," in raw_core and not large_parsed.reading_includes_suffix)
            )
            candidate = _korean_numeric_unit_candidate(
                raw_text,
                index,
                large_parsed.end,
                large_parsed.reading,
                inventory,
                ordered_units,
                "large_unit_registered_unit",
                render_core_reading=split_core,
                extra_metadata={
                    "numeric_reading": large_parsed.numeric_reading,
                    "numeric_span": large_parsed.numeric_span,
                    "suffix_span": large_parsed.suffix_span,
                    "has_decimal": large_parsed.has_decimal,
                },
            )
            if candidate is not None:
                candidates.append(candidate)
                index = candidate.full_span.end
                continue

        for marker in ("수십", "수백", "수천"):
            if raw_text.startswith(marker, index) and _valid_korean_numeric_unit_left_boundary(raw_text, index):
                candidate = _korean_numeric_unit_candidate(
                    raw_text,
                    index,
                    index + len(marker),
                    marker,
                    inventory,
                    ordered_units,
                    "quantified_korean_numeric_unit",
                )
                if candidate is not None:
                    candidates.append(candidate)
                    index = candidate.full_span.end
                    break
        else:
            index += 1
            continue
        continue
    return candidates


def parse_korean_numeric_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> Surface | None:
    if candidate.owner != "korean_numeric_unit":
        return None
    reading = candidate.metadata.get("reading")
    number_end = candidate.metadata.get("number_end")
    unit_start = candidate.metadata.get("unit_start")
    unit = candidate.metadata.get("unit")
    render_core_reading = candidate.metadata.get("render_core_reading") is True
    if not isinstance(reading, str):
        return None
    if not (
        isinstance(number_end, int)
        and isinstance(unit_start, int)
        and isinstance(unit, str)
        and candidate.core_span.start < number_end <= unit_start < candidate.core_span.end
    ):
        return None
    if render_core_reading:
        numeric_reading = candidate.metadata.get("numeric_reading")
        numeric_span = candidate.metadata.get("numeric_span")
        suffix_span = candidate.metadata.get("suffix_span")
        has_decimal = candidate.metadata.get("has_decimal") is True
        if not (
            isinstance(numeric_reading, str)
            and numeric_reading
            and isinstance(numeric_span, SourceSpan)
            and isinstance(suffix_span, SourceSpan)
        ):
            return None
        pieces = [
            RenderPiece(
                text=numeric_reading,
                provenance="GENERATED_READING",
                source_span=numeric_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        ]
        if has_decimal:
            pieces.append(
                RenderPiece(
                    text=SPOKEN_NUMERIC_BOUNDARY,
                    provenance="GENERATED_PUNCT",
                    source_span=suffix_span,
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
        pieces.append(
            RenderPiece(
                text=raw_text[suffix_span.start : suffix_span.end],
                provenance="ORIGINAL_KOREAN",
                source_span=suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        pieces.append(
            RenderPiece(
                text=SPOKEN_NUMERIC_BOUNDARY + candidate.metadata["unit_reading"],
                provenance="GENERATED_READING",
                source_span=SourceSpan(unit_start, candidate.core_span.end),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        return Surface(
            surface_type=candidate.surface_type or "KOREAN_NUMERIC_UNIT_SURFACE",
            owner=candidate.owner,
            raw=raw_text[candidate.core_span.start : candidate.core_span.end],
            span=candidate.core_span,
            reading=reading,
            render_pieces=pieces,
            metadata={"reason": candidate.reason},
        )
    pieces: list[RenderPiece] = []
    cursor = candidate.core_span.start
    while cursor < number_end:
        if _is_ascii_digit(raw_text[cursor]):
            digit_end = cursor
            while digit_end < number_end and _is_ascii_digit(raw_text[digit_end]):
                digit_end += 1
            digit_reading = read_spaced_integer_text(raw_text[cursor:digit_end])
            if digit_reading is None:
                return None
            pieces.append(
                RenderPiece(
                    text=digit_reading,
                    provenance="GENERATED_READING",
                    source_span=SourceSpan(cursor, digit_end),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
            cursor = digit_end
            continue
        korean_end = cursor
        while korean_end < number_end and not _is_ascii_digit(raw_text[korean_end]):
            korean_end += 1
        pieces.append(
            RenderPiece(
                text=raw_text[cursor:korean_end],
                provenance="ORIGINAL_KOREAN",
                source_span=SourceSpan(cursor, korean_end),
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
        cursor = korean_end
    pieces.append(
        RenderPiece(
            text=SPOKEN_NUMERIC_BOUNDARY + candidate.metadata["unit_reading"],
            provenance="GENERATED_READING",
            source_span=SourceSpan(unit_start, candidate.core_span.end),
            owner=candidate.owner,
            metadata={"surface_type": candidate.surface_type},
        )
    )
    return Surface(
        surface_type=candidate.surface_type or "KOREAN_NUMERIC_UNIT_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.core_span.start : candidate.core_span.end],
        span=candidate.core_span,
        reading=reading,
        render_pieces=pieces,
        metadata={"reason": candidate.reason},
    )


def _korean_numeric_unit_candidate(
    raw_text: str,
    start: int,
    number_end: int,
    number_reading: str,
    inventory: dict[str, str],
    ordered_units: list[str],
    reason: str,
    *,
    render_core_reading: bool = False,
    extra_metadata: dict[str, object] | None = None,
) -> SurfaceCandidate | None:
    unit_start = _consume_optional_ascii_space(raw_text, number_end)
    has_space_before_unit = unit_start != number_end
    for unit in ordered_units:
        if has_space_before_unit and not unit_allows_space_before(unit):
            continue
        if not raw_text.startswith(unit, unit_start):
            continue
        full_span = SourceSpan(start, unit_start + len(unit))
        if not _valid_korean_numeric_unit_boundary(raw_text, full_span):
            return None
        metadata: dict[str, object] = {
            "reading": f"{number_reading}{SPOKEN_NUMERIC_BOUNDARY}{inventory[unit]}",
            "core_reading": number_reading,
            "render_core_reading": render_core_reading,
            "unit": unit,
            "unit_reading": inventory[unit],
            "number_end": number_end,
            "unit_start": unit_start,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        return SurfaceCandidate(
            core_span=full_span,
            full_span=full_span,
            owner="korean_numeric_unit",
            surface_type="KOREAN_NUMERIC_UNIT_SURFACE",
            reason=reason,
            metadata=metadata,
        )
    return None


def _valid_korean_numeric_unit_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    previous = raw_text[start - 1]
    return not (
        previous.isascii() and previous.isalnum()
    ) and not ("\uac00" <= previous <= "\ud7a3") and previous not in {
        "_",
        "/",
        ".",
        ",",
        "~",
        "+",
        "-",
    }


def _valid_korean_numeric_unit_boundary(raw_text: str, span: SourceSpan) -> bool:
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    if next_char is None or next_char.isspace():
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    return next_char not in {"_", "/", "."}


def _is_hangul_syllable(char: str | None) -> bool:
    return (
        char is not None
        and len(char) == 1
        and _HANGUL_SYLLABLE_START <= ord(char) <= _HANGUL_SYLLABLE_END
    )


def _requires_left_hangul_context(unit: str) -> bool:
    # All-caps Latin units such as GB/MB also match acronym fallback when a
    # Hangul tail is attached. Require a Hangul neighbor on the left so
    # `GB그룹` stays an acronym while `수 GB` can still read as a unit.
    return bool(unit) and unit.isascii() and unit.isalpha() and unit.isupper() and len(unit) >= 2


def _hangul_run_preceded_by_digit(raw_text: str, hangul_index: int) -> bool:
    if not _is_hangul_syllable(raw_text[hangul_index]):
        return False
    index = hangul_index
    while index >= 0 and _is_hangul_syllable(raw_text[index]):
        index -= 1
    return index >= 0 and _is_ascii_digit(raw_text[index])


def _is_safe_hangul_context_anchor(raw_text: str, hangul_index: int) -> bool:
    return _is_hangul_syllable(raw_text[hangul_index]) and not _hangul_run_preceded_by_digit(
        raw_text, hangul_index
    )


def _has_left_hangul_context_neighbor(raw_text: str, start: int) -> bool:
    if start > 0 and _is_safe_hangul_context_anchor(raw_text, start - 1):
        return True
    return (
        start >= 2
        and raw_text[start - 1] == " "
        and _is_safe_hangul_context_anchor(raw_text, start - 2)
    )


def _has_hangul_context_neighbor(
    raw_text: str,
    start: int,
    end: int,
    *,
    require_left: bool = False,
) -> bool:
    if _has_left_hangul_context_neighbor(raw_text, start):
        return True
    if require_left:
        return False
    if end < len(raw_text) and _is_safe_hangul_context_anchor(raw_text, end):
        return True
    if (
        end + 1 < len(raw_text)
        and raw_text[end] == " "
        and _is_safe_hangul_context_anchor(raw_text, end + 1)
    ):
        return True
    return False


def _ascii_alpha_beyond_optional_space(
    raw_text: str, index: int, *, toward_left: bool
) -> bool:
    if toward_left:
        if index <= 0:
            return False
        previous = raw_text[index - 1]
        if previous == " ":
            if index < 2:
                return False
            previous = raw_text[index - 2]
        return previous.isascii() and previous.isalpha()
    if index >= len(raw_text):
        return False
    following = raw_text[index]
    if following == " ":
        if index + 1 >= len(raw_text):
            return False
        following = raw_text[index + 1]
    return following.isascii() and following.isalpha()


def _has_standalone_letter_free_context(raw_text: str, start: int, end: int) -> bool:
    return not _ascii_alpha_beyond_optional_space(
        raw_text, start, toward_left=True
    ) and not _ascii_alpha_beyond_optional_space(raw_text, end, toward_left=False)


def unit_allows_space_before(unit: str) -> bool:
    if not isinstance(unit, str):
        raise TypeError("unit must be str")
    return unit not in _ATTACHED_NUMERIC_ONLY_UNITS


def _valid_hangul_context_unit_boundary(raw_text: str, start: int, end: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    next_char = raw_text[end] if end < len(raw_text) else None
    next_next = raw_text[end + 1] if end + 1 < len(raw_text) else None
    next_non_space = raw_text[end:].lstrip()
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if prev_char in _PREV_BLOCKERS or prev_char in _PREV_SYMBOL_BLOCKERS:
            return False
        if prev_char in {"_"}:
            return False
    if next_char is None:
        return True
    if next_char in _SUPERSCRIPT_EXPONENTS:
        return False
    if next_char.isspace() and next_non_space.startswith("/"):
        return False
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in _NEXT_BLOCKERS and next_char != ",":
        return False
    if next_char == ".":
        return not (next_next is not None and next_next.isdigit())
    return next_char not in {"_"}


def scan_unit_contamination_preserve_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (_is_ascii_digit(raw_text[index]) or is_signed_numeric_sign(raw_text[index])):
            index += 1
            continue
        if _has_blocking_previous_context(raw_text, index):
            index += 1
            continue
        repeated_sign_candidate = _repeated_sign_unit_preserve_candidate(raw_text, index)
        if repeated_sign_candidate is not None:
            candidates.append(repeated_sign_candidate)
            index = repeated_sign_candidate.full_span.end
            continue
        suffix_spacing_candidate = _unit_suffix_spacing_preserve_candidate(
            raw_text, index
        )
        if suffix_spacing_candidate is not None:
            candidates.append(suffix_spacing_candidate)
            index = suffix_spacing_candidate.full_span.end
            continue
        numeric_start = index + 1 if is_signed_numeric_sign(raw_text[index]) else index
        numeric_end = _consume_decimal_number(raw_text, index)
        if is_signed_numeric_sign(raw_text[index]):
            numeric_end = _consume_decimal_number(raw_text, numeric_start)
        if numeric_end is None:
            index += 1
            continue
        candidate = _unit_tail_preserve_candidate(raw_text, index, numeric_end)
        if candidate is None:
            candidate = _compound_slash_tail_preserve_candidate(
                raw_text, index, numeric_end
            )
        if candidate is None:
            index += 1
            continue
        candidates.append(candidate)
        index = candidate.full_span.end
    return candidates


def parse_unit_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    if candidate.owner not in {"caret_power_unit", "simple_unit", "special_unit"}:
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    parsed = _parse_surface(raw)
    return parsed[2] if parsed is not None else None


def is_free_standing_je_before(raw_text: str, start: int) -> bool:
    """True when a lone ``제`` sits immediately before ``start``.

    ``제10kg`` may then leave ``제`` in place and let the unit owner read the
    number. Glued forms such as ``A제10kg`` stay blocked.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if start < 1 or raw_text[start - 1] != "제":
        return False
    je_index = start - 1
    return je_index == 0 or raw_text[je_index - 1].isspace()


def starts_with_supported_unit(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if any(text.startswith(unit) for unit in _SIMPLE_UNITS_BY_LENGTH + _SPECIAL_UNITS_BY_LENGTH):
        return True
    from engine.span_engine.compound_unit import starts_with_supported_compound_exact_unit

    return starts_with_supported_compound_exact_unit(text)


def supported_unit_prefix_length(text: str) -> int | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    for unit in _SIMPLE_UNITS_BY_LENGTH + _SPECIAL_UNITS_BY_LENGTH:
        if text.startswith(unit):
            return len(unit)
    return None


def _range_compatible_readings() -> dict[str, str]:
    from engine.span_engine.compound_unit import COMPOUND_EXACT_UNIT_NAMES

    return {**RANGE_COMPATIBLE_UNIT_READINGS, **COMPOUND_EXACT_UNIT_NAMES}


def range_compatible_unit_reading(unit: str) -> str | None:
    if not isinstance(unit, str):
        raise TypeError("unit must be str")
    return _range_compatible_readings().get(unit)


def range_compatible_units_by_length() -> list[str]:
    return sorted(_range_compatible_readings(), key=len, reverse=True)


def _scan_unit_candidates(
    raw_text: str,
    inventory: dict[str, str],
    ordered_units: list[str],
    owner: str,
    surface_type: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (_is_ascii_digit(raw_text[index]) or is_signed_numeric_sign(raw_text[index])):
            index += 1
            continue
        amount_start = index
        numeric_start = amount_start + 1 if is_signed_numeric_sign(raw_text[amount_start]) else amount_start
        amount_end = _consume_decimal_number(raw_text, numeric_start)
        if amount_end is None:
            index += 1
            continue
        amount = raw_text[amount_start:amount_end]
        unit_start = _consume_optional_ascii_space(raw_text, amount_end)
        has_decimal_amount = "." in amount
        has_space_before_unit = unit_start != amount_end
        for unit in ordered_units:
            unit_name = inventory[unit]
            if not raw_text.startswith(unit, unit_start):
                continue
            if has_space_before_unit and not unit_allows_space_before(unit):
                continue
            if has_decimal_amount and not _unit_allows_decimal_amount(unit, owner):
                continue
            span = SourceSpan(amount_start, unit_start + len(unit))
            if not _valid_amount_and_boundary(raw_text, span, amount):
                continue
            if owner == "caret_power_unit" and not _valid_caret_power_boundary(raw_text, span.end):
                continue
            candidates.append(
                SurfaceCandidate(
                    core_span=span,
                    full_span=span,
                    owner=owner,
                    surface_type=surface_type,
                    reason=f"{owner}_numeric_prefix",
                    metadata={
                        "amount": amount,
                        "unit": unit,
                        "unit_reading": unit_name,
                        "reading": _reading(amount, unit_name),
                        **_signed_contract_metadata(amount, owner),
                    },
                )
            )
            break
        index = max(amount_end, index + 1)
    return candidates


def _parse_surface(raw: str) -> tuple[str, str, str] | None:
    for inventory, ordered_units in (
        (CARET_POWER_UNIT_READINGS, _CARET_POWER_UNITS_BY_LENGTH),
        (SIMPLE_UNIT_READINGS, _SIMPLE_UNITS_BY_LENGTH),
        (SPECIAL_UNIT_READINGS, _SPECIAL_UNITS_BY_LENGTH),
    ):
        for unit in ordered_units:
            if raw.endswith(unit):
                amount = raw[: -len(unit)].strip()
                unsigned_amount = _unsigned_amount(amount)
                if unsigned_amount is not None and _is_valid_number(unsigned_amount):
                    unit_name = inventory[unit]
                    return amount, unit_name, _reading(amount, unit_name)
                if unsigned_amount is not None and _is_supported_decimal_amount(unsigned_amount):
                    unit_name = inventory[unit]
                    return amount, unit_name, _reading(amount, unit_name)
    return None


def _reading(amount: str, unit_name: str) -> str:
    amount_reading = _amount_reading(amount)
    if unit_name == "화씨":
        return f"화씨 {amount_reading}도"
    separator = "" if unit_name == "도" else SPOKEN_NUMERIC_BOUNDARY
    return f"{amount_reading}{separator}{unit_name}"


def _amount_reading(amount: str) -> str:
    policy = SIGNED_OWNER_POLICIES["simple_unit"]
    core = parse_signed_numeric_core(
        amount,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        raise ValueError("invalid signed unit amount")
    reading = _plus_decimal_amount_reading(core.number.raw)
    signed_reading = apply_sign_profile(
        reading,
        core.sign_kind,
        sign_profile=policy.sign_profile,
    )
    if signed_reading is None:
        raise ValueError("unit owner rejects numeric sign")
    return signed_reading


def _signed_contract_metadata(amount: str, owner: str) -> dict[str, object]:
    policy_key = "special_unit" if owner == "special_unit" else "simple_unit"
    policy = SIGNED_OWNER_POLICIES[policy_key]
    core = parse_signed_numeric_core(
        amount,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        return {}
    return {
        "sign_profile": policy.sign_profile.value,
        "numeric_form": core.numeric_form,
        "sign_surface": core.sign_surface,
    }


def _plus_decimal_amount_reading(amount: str) -> str:
    return read_decimal_amount_text(
        amount,
        overflow_message="unit amount must be below 100000000",
    )


def _unsigned_amount(amount: str) -> str | None:
    sign, unsigned = strip_signed_numeric_sign(amount)
    if sign is not None:
        return unsigned if unsigned else None
    return amount


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_supported_decimal_amount(text: str) -> bool:
    integer_part, dot, fractional_part = text.partition(".")
    if not dot:
        return _is_valid_number(integer_part)
    return _is_valid_number(integer_part) and _is_ascii_digits(fractional_part)


def _consume_decimal_number(raw_text: str, start: int) -> int | None:
    integer_end = _consume_integer(raw_text, start)
    if integer_end is None:
        return None
    if integer_end < len(raw_text) and raw_text[integer_end] == ".":
        fraction_start = integer_end + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return integer_end
        return fraction_end
    return integer_end


def _consume_integer(raw_text: str, start: int) -> int | None:
    digit_end = _consume_digits(raw_text, start)
    if digit_end == start:
        return None
    if digit_end >= len(raw_text) or raw_text[digit_end] != ",":
        return digit_end
    if digit_end - start > 3:
        return None
    index = digit_end
    while index < len(raw_text) and raw_text[index] == ",":
        group_start = index + 1
        group_end = _consume_digits(raw_text, group_start)
        if group_end - group_start != 3:
            return None
        index = group_end
    if index < len(raw_text) and raw_text[index] == ",":
        return None
    return index


def _is_valid_number(text: str) -> bool:
    if not text:
        return False
    if "," not in text:
        return _is_ascii_digits(text)
    groups = text.split(",")
    if not (1 <= len(groups[0]) <= 3 and _is_ascii_digits(groups[0])):
        return False
    return all(len(group) == 3 and _is_ascii_digits(group) for group in groups[1:])


def _has_blocking_previous_context(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return False
    if prev_char.isascii() and prev_char.isalnum():
        return True
    if "\uac00" <= prev_char <= "\ud7a3":
        return not is_free_standing_je_before(raw_text, start)
    return prev_char in _PREV_BLOCKERS or prev_char in _PREV_SYMBOL_BLOCKERS


def _unit_tail_preserve_candidate(
    raw_text: str, start: int, numeric_end: int
) -> SurfaceCandidate | None:
    unit_start = _consume_optional_ascii_space(raw_text, numeric_end)
    for exact_unit in _COMPOUND_EXACT_UNIT_SURFACES:
        if not raw_text.startswith(exact_unit, unit_start):
            continue
        exact_end = unit_start + len(exact_unit)
        if _consume_unsafe_ascii_tail(raw_text, exact_end) == exact_end:
            return None
    for unit in _UNSAFE_TAIL_UNITS_BY_LENGTH:
        if not raw_text.startswith(unit, unit_start):
            continue
        unit_end = unit_start + len(unit)
        data_rate_slash_space_end = _consume_data_rate_slash_space_tail(
            raw_text, unit, unit_end
        )
        if data_rate_slash_space_end is not None:
            return _preserve_candidate(
                start,
                data_rate_slash_space_end,
                "data_rate_slash_space_non_goal_preserve",
            )
        tail_end = _consume_unsafe_ascii_tail(raw_text, unit_end)
        if tail_end == unit_end:
            return None
        return _preserve_candidate(
            start,
            tail_end,
            "unit_like_ascii_tail_contamination",
        )
    if unit_start < len(raw_text):
        symbol = raw_text[unit_start]
        if (
            symbol != "㎧"
            and _CJK_COMPATIBILITY_UNIT_SYMBOL_START
            <= ord(symbol)
            <= _CJK_COMPATIBILITY_UNIT_SYMBOL_END
        ):
            symbol_end = unit_start + 1
            tail_end = _consume_unsafe_ascii_tail(raw_text, symbol_end)
            return _preserve_candidate(
                start,
                tail_end,
                "unregistered_compatibility_unit_symbol_preserve",
            )
    return None


def _unit_suffix_spacing_preserve_candidate(
    raw_text: str, start: int
) -> SurfaceCandidate | None:
    amount_end = _consume_numeric_like_surface(raw_text, start)
    if amount_end is None:
        return None
    space_end = amount_end
    while space_end < len(raw_text) and raw_text[space_end].isspace():
        space_end += 1
    spacing = raw_text[amount_end:space_end]
    unit = _supported_unit_at(raw_text, space_end)
    if unit is None:
        return None
    amount = raw_text[start:amount_end]
    if _is_valid_signed_decimal_amount(amount) and spacing in {"", " "}:
        return None
    return _preserve_candidate(
        start,
        space_end + len(unit),
        "unit_percent_suffix_invalid_or_disallowed_spacing_preserve",
    )


def _repeated_sign_unit_preserve_candidate(
    raw_text: str, start: int
) -> SurfaceCandidate | None:
    if not is_signed_numeric_sign(raw_text[start]):
        return None
    index = start + 1
    if index >= len(raw_text) or not is_signed_numeric_sign(raw_text[index]):
        return None
    while index < len(raw_text) and is_signed_numeric_sign(raw_text[index]):
        index += 1
    numeric_end = _consume_decimal_number(raw_text, index)
    if numeric_end is None:
        return None
    unit_start = _consume_optional_ascii_space(raw_text, numeric_end)
    unit = _supported_unit_at(raw_text, unit_start)
    if unit is None:
        return None
    return _preserve_candidate(
        start,
        unit_start + len(unit),
        "unit_percent_repeated_sign_preserve",
    )


def _consume_numeric_like_surface(raw_text: str, start: int) -> int | None:
    index = start
    if index < len(raw_text) and is_signed_numeric_sign(raw_text[index]):
        index += 1
    numeric_start = index
    while index < len(raw_text) and (
        _is_ascii_digit(raw_text[index]) or raw_text[index] in {",", "."}
    ):
        index += 1
    if index == numeric_start:
        return None
    return index


def _supported_unit_at(raw_text: str, start: int) -> str | None:
    from engine.span_engine.compound_unit import COMPOUND_EXACT_UNIT_NAMES

    for unit in (
        _SIMPLE_UNITS_BY_LENGTH
        + _SPECIAL_UNITS_BY_LENGTH
        + sorted(COMPOUND_EXACT_UNIT_NAMES, key=len, reverse=True)
    ):
        if raw_text.startswith(unit, start):
            return unit
    return None


def _is_valid_signed_decimal_amount(amount: str) -> bool:
    policy = SIGNED_OWNER_POLICIES["simple_unit"]
    core = parse_signed_numeric_core(
        amount,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        return False
    return _is_valid_integer_amount(core.integer_raw)


def _is_valid_integer_amount(integer_part: str) -> bool:
    if not _is_valid_number(integer_part):
        return False
    digits = integer_part.replace(",", "")
    return len(digits) == 1 or not digits.startswith("0")


def _consume_data_rate_slash_space_tail(
    raw_text: str, unit: str, unit_end: int
) -> int | None:
    if unit not in _DATA_RATE_NUMERATOR_PREFIXES:
        return None
    if not raw_text.startswith(" / ", unit_end):
        return None
    tail_start = unit_end + 3
    if not raw_text.startswith("s", tail_start):
        return None
    tail_end = tail_start + 1
    if _consume_unsafe_ascii_tail(raw_text, tail_end) != tail_end:
        return None
    return tail_end


def _compound_slash_tail_preserve_candidate(
    raw_text: str, start: int, numeric_end: int
) -> SurfaceCandidate | None:
    segment_start = _consume_optional_ascii_space(raw_text, numeric_end)
    if raw_text.startswith("㎧", segment_start):
        symbol_end = segment_start + 1
        tail_end = _consume_unsafe_ascii_tail(raw_text, symbol_end)
        if tail_end == symbol_end:
            return None
        return _preserve_candidate(
            start,
            tail_end,
            "compound_unit_like_ascii_tail_contamination",
        )
    segment_end = segment_start
    while segment_end < len(raw_text) and (
        raw_text[segment_end].isascii()
        and raw_text[segment_end].isalpha()
        or raw_text[segment_end] in {"㎞", "㎎", "ℓ", "/", "／"}
    ):
        segment_end += 1
    if segment_end == segment_start or not any(
        slash in raw_text[segment_start:segment_end] for slash in {"/", "／"}
    ):
        return None
    segment = raw_text[segment_start:segment_end]
    normalized_segment = segment.replace("／", "/")
    numerator = normalized_segment.split("/", 1)[0]
    if numerator not in _COMPOUND_SLASH_NUMERATOR_PREFIXES:
        return None
    if segment in _COMPOUND_SLASH_UNIT_SURFACES:
        return None
    return _preserve_candidate(
        start,
        segment_end,
        "compound_unit_like_ascii_tail_contamination",
    )


def _consume_unsafe_ascii_tail(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if not (char.isascii() and char.isalnum()):
            break
        index += 1
    return index


def _preserve_candidate(start: int, end: int, reason: str) -> SurfaceCandidate:
    span = SourceSpan(start, end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="UNIT_CONTAMINATION_PRESERVE_SURFACE",
        reason=reason,
    )


def _valid_amount_and_boundary(raw_text: str, span: SourceSpan, amount: str) -> bool:
    unsigned_amount = _unsigned_amount(amount)
    if unsigned_amount is None:
        return False
    integer_part = unsigned_amount.split(".", 1)[0].replace(",", "")
    if len(integer_part) > 1 and integer_part.startswith("0"):
        return False
    if int(integer_part) >= 100000000:
        return False
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
    next_non_space = raw_text[span.end :].lstrip()
    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            if not is_free_standing_je_before(raw_text, span.start):
                return False
        if prev_char in _PREV_BLOCKERS:
            return False
        if prev_char in _PREV_SYMBOL_BLOCKERS:
            return False
    if next_char is None:
        return True
    if next_char in _SUPERSCRIPT_EXPONENTS:
        return False
    if next_char.isspace() and next_non_space.startswith("/"):
        return False
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in _NEXT_BLOCKERS and next_char != ",":
        return False
    if next_char == ".":
        return not (next_next is not None and next_next.isdigit())
    return True

def _unit_allows_decimal_amount(unit: str, owner: str) -> bool:
    if owner == "caret_power_unit":
        return unit[:-2] in _DECIMAL_AMOUNT_UNIT_SURFACES
    return unit in _DECIMAL_AMOUNT_UNIT_SURFACES


def _valid_caret_power_boundary(raw_text: str, end: int) -> bool:
    if end == len(raw_text):
        return True
    next_char = raw_text[end]
    return (
        next_char.isspace()
        or "\uac00" <= next_char <= "\ud7a3"
        or next_char in {".", ",", "!", "?", ";", ":", ")", "]", "}"}
    )


def _valid_caret_literal_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    previous = raw_text[start - 1]
    return not (
        previous.isascii()
        and previous.isalnum()
        or "\uac00" <= previous <= "\ud7a3"
        or previous in _PREV_BLOCKERS
    )


def _caret_numeric_like_start(raw_text: str, start: int) -> int:
    index = start
    while index > 0 and (
        _is_ascii_digit(raw_text[index - 1])
        or raw_text[index - 1] in {",", "."}
        or is_signed_numeric_sign(raw_text[index - 1])
    ):
        index -= 1
    return index


def _scan_bare_caret_literal_preserves(
    raw_text: str,
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (raw_text[index].isascii() and raw_text[index].isalpha()):
            index += 1
            continue
        start = index
        while index < len(raw_text) and (
            raw_text[index].isascii() and raw_text[index].isalpha()
        ):
            index += 1
        if index >= len(raw_text) or raw_text[index] != "^":
            continue
        exponent_end = index + 1
        while exponent_end < len(raw_text) and (
            raw_text[exponent_end].isascii()
            and raw_text[exponent_end].isalnum()
        ):
            exponent_end += 1
        if exponent_end == index + 1:
            continue
        previous = raw_text[start - 1] if start > 0 else None
        preceded_by_numeric = (
            previous is not None
            and previous.isascii()
            and previous.isdigit()
        ) or (
            previous == " "
            and start >= 2
            and raw_text[start - 2].isascii()
            and raw_text[start - 2].isdigit()
        )
        if preceded_by_numeric:
            index = exponent_end
            continue
        span = SourceSpan(start, exponent_end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="CARET_LITERAL_PRESERVE_SURFACE",
                reason="bare_caret_literal_preserve",
            )
        )
        index = exponent_end
    return candidates


def _scan_spaced_caret_literal_preserves(
    raw_text: str,
) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for caret_index, char in enumerate(raw_text):
        if char != "^" or caret_index == 0 or raw_text[caret_index - 1] != " ":
            continue
        previous_index = caret_index - 2
        if previous_index < 0 or not (
            raw_text[previous_index].isascii()
            and raw_text[previous_index].isalpha()
        ):
            continue
        end = caret_index + 1
        while end < len(raw_text) and (
            raw_text[end].isascii() and raw_text[end].isalnum()
        ):
            end += 1
        if end == caret_index + 1:
            continue
        span = SourceSpan(caret_index, end)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="CARET_LITERAL_PRESERVE_SURFACE",
                reason="spaced_caret_literal_preserve",
            )
        )
    return candidates


__all__ = [
    "CARET_POWER_UNIT_READINGS",
    "HANGUL_CONTEXT_UNIT_EXCLUSIONS",
    "HANGUL_CONTEXT_UNIT_READINGS",
    "RANGE_COMPATIBLE_UNIT_READINGS",
    "SIMPLE_UNIT_READINGS",
    "SPECIAL_UNIT_READINGS",
    "parse_korean_numeric_unit_candidate",
    "parse_unit_candidate",
    "parse_caret_literal_unit_candidate",
    "range_compatible_unit_reading",
    "range_compatible_units_by_length",
    "scan_caret_power_unit_candidates",
    "scan_caret_literal_unit_candidates",
    "scan_simple_unit_candidates",
    "scan_special_unit_candidates",
    "scan_hangul_context_unit_candidates",
    "scan_korean_numeric_unit_candidates",
    "scan_unit_contamination_preserve_candidates",
    "supported_unit_prefix_length",
    "is_free_standing_je_before",
    "starts_with_supported_unit",
    "unit_allows_space_before",
]
