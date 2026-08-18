from __future__ import annotations

from engine.span_engine.brackets import BracketRange
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.sign_aliases import (
    SIGNED_NUMERIC_SIGN_ALIASES,
    is_signed_numeric_sign,
    strip_signed_numeric_sign,
)
from engine.span_engine.residual_spacing import needs_residual_hangul_space
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    SignProfile,
    apply_sign_profile,
    parse_sign_surface,
    parse_signed_numeric_core,
    render_signed_numeric,
)
from engine.span_engine.units import starts_with_supported_unit

_ALLOWED_TAILS = (
    "",
    "였고",
    "였지만",
    "였다",
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
    "이다",
    "다",
    "입니다",
)

_TAIL_PUNCTUATION = frozenset({".", ",", "!", "?", ";", ":", "…", "。", "，", "！", "？"})
_CELSIUS_UNITS = frozenset({"℃", "ºC", "°C", "º C", "° C"})
_FAHRENHEIT_UNITS = frozenset({"℉", "ºF", "°F", "º F", "° F"})
_SIGN_CHARS = SIGNED_NUMERIC_SIGN_ALIASES
# Both ASCII degree ° and ordinal indicator º are treated as bare degree.
_BARE_DEGREE_UNITS = frozenset({"°", "º"})
_SIGNED_TEMPERATURE_UNITS = tuple(
    sorted(_CELSIUS_UNITS | _FAHRENHEIT_UNITS, key=len, reverse=True)
)
_CONTEXTUAL_HANGUL_NUMERIC_UNITS = frozenset(
    {
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
        "시",
        "시간",
        "시리즈",
        "분기",
    }
)


def parse_signed_numeric(raw_number: str) -> str | None:
    if not isinstance(raw_number, str):
        raise TypeError("raw_number must be str")
    core = parse_signed_numeric_core(raw_number.strip())
    if core is None:
        return None
    return render_signed_numeric(core, sign_profile=SignProfile.DEFAULT)


def signed_temperature_reading(
    sign: str,
    numeric: str,
    unit: str = "℃",
    *,
    suppress_unit_label: bool = False,
) -> str | None:
    policy = SIGNED_OWNER_POLICIES["signed_temperature"]
    numeric = numeric.strip()
    core = parse_signed_numeric_core(
        sign + numeric,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        require_sign=True,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        return None
    reading = render_signed_numeric(
        core,
        sign_profile=policy.sign_profile,
    )
    if reading is None:
        return None
    reading = f"{reading}도"
    if unit in _FAHRENHEIT_UNITS and not suppress_unit_label:
        return f"화씨 {reading}"
    if unit in _FAHRENHEIT_UNITS or unit in _CELSIUS_UNITS:
        return reading
    return None


def signed_degree_reading(sign: str, numeric: str, unit: str = "°") -> str | None:
    """Return the existing angle or temperature-like bare-degree reading."""
    policy = SIGNED_OWNER_POLICIES["signed_degree"]
    numeric = numeric.strip()
    core = parse_signed_numeric_core(
        sign + numeric,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        require_sign=True,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        return None
    profile = SignProfile.TEMPERATURE if unit == "º" else SignProfile.DEFAULT
    reading = render_signed_numeric(core, sign_profile=profile)
    if reading is None:
        return None
    return f"{reading}도"


def scan_signed_temperature_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    candidates = _scan_invalid_signed_temperature_preserve_candidates(
        raw_text, excluded_ranges
    )
    for unit in _SIGNED_TEMPERATURE_UNITS:
        candidates.extend(
            _scan_signed_candidates(
                raw_text, excluded_ranges, unit, "signed_temperature"
            )
        )
    return sorted(candidates, key=lambda x: x.core_span.start)


def scan_signed_degree_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    """Scan for signed bare-degree tokens (both ° and º)."""
    candidates = _scan_invalid_signed_degree_preserve_candidates(
        raw_text, excluded_ranges
    )
    for unit in sorted(_BARE_DEGREE_UNITS, key=len, reverse=True):
        candidates.extend(
            _scan_signed_candidates(raw_text, excluded_ranges, unit, "signed_degree")
        )
    return sorted(candidates, key=lambda x: x.core_span.start)


def scan_signed_number_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    return _scan_signed_candidates(raw_text, excluded_ranges, "", "signed_number")


_PLUS_MINUS_SYMBOL = "\u00b1"


def scan_compound_signed_number_candidates(
    raw_text: str, excluded_ranges: list[BracketRange] | None = None
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text.startswith("+-", index):
            sign_len = 2
        elif raw_text[index] == _PLUS_MINUS_SYMBOL:
            sign_len = 1
        else:
            index += 1
            continue
        if _is_blocked_start(raw_text, index, "signed_number"):
            index += 1
            continue
        number_start = index + sign_len
        number_end = _consume_digits_and_commas(raw_text, number_start)
        if number_end == number_start:
            index += 1
            continue
        if number_end < len(raw_text) and raw_text[number_end] == ".":
            fraction_end = _consume_digits(raw_text, number_end + 1)
            if fraction_end == number_end + 1:
                index += 1
                continue
            number_end = fraction_end
        span = SourceSpan(index, number_end)
        if (
            _span_overlaps_excluded_range(span, excluded_ranges)
            or not _valid_boundaries(raw_text, span, "")
        ):
            index += 1
            continue
        tail = raw_text[span.end :]
        if not _tail_is_allowed_for_owner(tail, "signed_number"):
            index += 1
            continue
        core = parse_signed_numeric_core(raw_text[number_start:number_end])
        number_reading = render_signed_numeric(core) if core is not None else None
        if number_reading is None:
            index += 1
            continue
        reading = f"플러스 마이너스 {number_reading}"
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="signed_number",
                surface_type="COMPOUND_SIGNED_NUMBER_SURFACE",
                reason="compound_plus_minus_signed_number_surface",
                metadata={
                    "reading": reading,
                    "tail": _tail_prefix(tail),
                    "sign_profile": SignProfile.DEFAULT.value,
                    "numeric_form": core.numeric_form,
                    "sign_surface": raw_text[index : index + sign_len],
                    "compound_sign_sequence": True,
                },
            )
        )
        index = span.end
    return candidates


def scan_invalid_signed_numeric_preserve_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None = None,
) -> list[SurfaceCandidate]:
    """Atomically preserve malformed or unsupported direct-sign tokens.

    This scanner is intentionally registered after all supported structured
    signed owners and before generic decimal/number fallback.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    from engine.span_engine.phone import is_international_phone

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        if _is_blocked_start(raw_text, index, "signed_number"):
            index += 1
            continue
        if index + 1 >= len(raw_text) or raw_text[index + 1].isspace():
            index += 1
            continue
        phone_end = _consume_international_phone_prefix(raw_text, index)
        if is_international_phone(raw_text[index:phone_end]):
            index = phone_end
            continue
        end = _consume_signed_looking_token(raw_text, index)
        if end <= index + 1:
            index += 1
            continue
        span = SourceSpan(index, end)
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index = end
            continue
        raw = raw_text[index:end]
        if not any(_is_ascii_digit(char) for char in raw):
            index += 1
            continue
        if is_international_phone(raw):
            index = end
            continue
        if parse_signed_numeric_core(raw, require_sign=True) is not None:
            index = end
            continue
        sign_surface = raw[0]
        sign_kind = parse_sign_surface(sign_surface)
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="INVALID_OR_UNSUPPORTED_SIGNED_NUMERIC_PRESERVE_SURFACE",
                reason="invalid_or_unsupported_signed_numeric_surface_preserve",
                metadata={
                    "sign_profile": SignProfile.DEFAULT.value,
                    "sign_surface": sign_surface,
                    "sign_kind": sign_kind.value if sign_kind is not None else None,
                    "preserve_reason": "full_consume_or_owner_support_failed",
                },
            )
        )
        index = end
    return candidates


def _consume_international_phone_prefix(raw_text: str, start: int) -> int:
    index = start + 1
    while index < len(raw_text) and (
        _is_ascii_digit(raw_text[index]) or raw_text[index] == "-"
    ):
        index += 1
    return index


def _consume_signed_looking_token(raw_text: str, start: int) -> int:
    index = start + 1
    hard_stops = frozenset(
        {'!', '?', ';', ':', '…', '。', '，', '！', '？', '(', ')', '[', ']', '{', '}', '"', "'", chr(96)}
    )
    while index < len(raw_text):
        char = raw_text[index]
        if char.isspace() or char in hard_stops:
            break
        if char == "," and (
            index + 1 >= len(raw_text) or not _is_ascii_digit(raw_text[index + 1])
        ):
            break
        if char == ".":
            next_char = raw_text[index + 1] if index + 1 < len(raw_text) else None
            if next_char is not None and not (
                _is_ascii_digit(next_char)
                or (next_char.isascii() and next_char.isalpha())
                or _is_hangul_syllable(next_char)
            ):
                break
        index += 1
    return index


def parse_signed_candidate(raw_text: str, candidate: SurfaceCandidate) -> str | None:
    compound_reading = candidate.metadata.get("reading")
    if (
        candidate.metadata.get("compound_sign_sequence") is True
        and isinstance(compound_reading, str)
    ):
        return _with_residual_hangul_spacing(raw_text, candidate, compound_reading)
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    parsed = _parse_signed_surface(raw)
    if parsed is None:
        return None
    sign, numeric, unit = parsed
    if unit in _CELSIUS_UNITS or unit in _FAHRENHEIT_UNITS:
        return signed_temperature_reading(
            sign,
            numeric,
            unit,
            suppress_unit_label=_has_matching_temperature_label_context(
                raw_text, candidate.core_span.start, unit
            ),
        )
    if unit in _BARE_DEGREE_UNITS:
        return signed_degree_reading(sign, numeric, unit)
    if unit == "":
        policy = SIGNED_OWNER_POLICIES["signed_number"]
        core = parse_signed_numeric_core(
            sign + numeric,
            allow_plus=policy.accepts_plus,
            allow_minus=policy.accepts_minus,
            minus_aliases=policy.minus_aliases,
            require_sign=True,
            numeric_forms=policy.numeric_forms,
        )
        if core is None:
            return None
        tail = raw_text[candidate.core_span.end :]
        if tail.startswith("조각"):
            piece_reading = _signed_piece_reading(core, policy.sign_profile)
            if piece_reading is not None:
                return piece_reading
        reading = render_signed_numeric(core, sign_profile=policy.sign_profile)
        if reading is None:
            return None
        return _with_residual_hangul_spacing(raw_text, candidate, reading)
    return None


def _with_residual_hangul_spacing(
    raw_text: str, candidate: SurfaceCandidate, reading: str
) -> str:
    if needs_residual_hangul_space(raw_text, candidate.core_span.end):
        return f"{reading} "
    return reading


def _signed_piece_reading(core, sign_profile: SignProfile) -> str | None:
    if not core.has_decimal:
        from engine.span_engine.counter import counter_number_reading

        counter_reading = counter_number_reading(core.integer_raw, "조각")
        if counter_reading is not None:
            return apply_sign_profile(
                counter_reading,
                core.sign_kind,
                sign_profile=sign_profile,
            )
    reading = render_signed_numeric(core, sign_profile=sign_profile)
    if reading is None:
        return None
    return f"{reading} "


def _scan_signed_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None,
    unit: str,
    owner: str,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        if _is_blocked_start(raw_text, index, owner):
            index += 1
            continue
        span = _scan_signed_span(raw_text, index, unit)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        tail = raw_text[span.end :]
        if (
            owner == "signed_number"
            and _signed_span_is_decimal(raw_text, span)
            and _tail_starts_with_registered_numeric_suffix(tail)
        ):
            index += 1
            continue
        if not _tail_is_allowed_for_owner(tail, owner):
            index += 1
            continue
        reading = parse_signed_candidate(
            raw_text,
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner=owner,
                surface_type="SIGNED_SURFACE",
            ),
        )
        if reading is None:
            index += 1
            continue
        
        if owner == "signed_temperature":
            surface_type = "SIGNED_TEMPERATURE_SURFACE"
        elif owner == "signed_degree":
            surface_type = "SIGNED_DEGREE_SURFACE"
        else:
            surface_type = "SIGNED_NUMBER_SURFACE"

        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner=owner,
                surface_type=surface_type,
                reason=f"{owner}_surface",
                metadata=_signed_candidate_metadata(
                    raw_text[span.start : span.end],
                    reading,
                    _tail_prefix(tail),
                    owner,
                ),
            )
        )
        index = span.end
    return candidates


def _signed_candidate_metadata(
    raw: str,
    reading: str,
    tail: str | None,
    owner: str,
) -> dict[str, object]:
    parsed = _parse_signed_surface(raw)
    if parsed is None:
        return {"reading": reading, "tail": tail}
    sign, numeric, unit = parsed
    policy = SIGNED_OWNER_POLICIES[owner]
    core = parse_signed_numeric_core(
        sign + numeric,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        require_sign=True,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        return {"reading": reading, "tail": tail}
    profile = policy.sign_profile
    if owner == "signed_degree":
        profile = SignProfile.TEMPERATURE if unit == "º" else SignProfile.DEFAULT
    return {
        "reading": reading,
        "tail": tail,
        "sign_profile": profile.value,
        "numeric_form": core.numeric_form,
        "sign_surface": core.sign_surface,
    }


def _scan_invalid_signed_temperature_preserve_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        span = _scan_numeric_temperature_span(raw_text, index)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        if _is_valid_signed_temperature_surface(raw_text, index, span):
            index = span.end
            continue
        full_span = SourceSpan(span.start, _consume_ascii_tail(raw_text, span.end))
        candidates.append(
            SurfaceCandidate(
                core_span=full_span,
                full_span=full_span,
                owner="preserve",
                surface_type="INVALID_SIGNED_TEMPERATURE_PRESERVE_SURFACE",
                reason="invalid_signed_temperature_dot_fraction_preserve",
            )
        )
        index = full_span.end
    return candidates


def _scan_invalid_signed_degree_preserve_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []

    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        span = _scan_numeric_degree_span(raw_text, index)
        if span is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index += 1
            continue
        if _is_valid_signed_degree_surface(raw_text, index, span):
            index = span.end
            continue
        full_span = SourceSpan(span.start, _consume_ascii_tail(raw_text, span.end))
        candidates.append(
            SurfaceCandidate(
                core_span=full_span,
                full_span=full_span,
                owner="preserve",
                surface_type="INVALID_SIGNED_DEGREE_PRESERVE_SURFACE",
                reason="invalid_signed_degree_preserve",
            )
        )
        index = full_span.end
    return candidates


def _scan_dot_fraction_temperature_span(raw_text: str, start: int) -> SourceSpan | None:
    index = start + 1
    if index >= len(raw_text) or raw_text[index] != ".":
        return None
    fraction_start = index + 1
    fraction_end = _consume_digits(raw_text, fraction_start)
    if fraction_end == fraction_start:
        return None
    for unit in _SIGNED_TEMPERATURE_UNITS:
        if raw_text.startswith(unit, fraction_end):
            return SourceSpan(start, fraction_end + len(unit))
    return None


def _scan_numeric_temperature_span(raw_text: str, start: int) -> SourceSpan | None:
    numeric_end = _consume_signed_numeric_end(raw_text, start)
    if numeric_end is None:
        return _scan_dot_fraction_temperature_span(raw_text, start)
    for unit in _SIGNED_TEMPERATURE_UNITS:
        if raw_text.startswith(unit, numeric_end):
            return SourceSpan(start, numeric_end + len(unit))
    return None


def _scan_numeric_degree_span(raw_text: str, start: int) -> SourceSpan | None:
    numeric_end = _consume_signed_numeric_end(raw_text, start)
    if numeric_end is None:
        return None
    for unit in sorted(_BARE_DEGREE_UNITS, key=len, reverse=True):
        if raw_text.startswith(unit, numeric_end):
            return SourceSpan(start, numeric_end + len(unit))
    return None


def _consume_signed_numeric_end(raw_text: str, start: int) -> int | None:
    index = start + 1
    integer_end = _consume_digits_and_commas(raw_text, index)
    if integer_end == index:
        return None
    index = integer_end
    if index < len(raw_text) and raw_text[index] == ".":
        fraction_start = index + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        index = fraction_end
    return index


def _consume_ascii_tail(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and raw_text[index].isascii() and raw_text[index].isalnum():
        index += 1
    return index


def _scan_signed_span(raw_text: str, start: int, unit: str) -> SourceSpan | None:
    index = start + 1
    integer_end = _consume_digits_and_commas(raw_text, index)
    if integer_end == index:
        return None
    index = integer_end
    if index < len(raw_text) and raw_text[index] == ".":
        fraction_start = index + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        index = fraction_end
    
    if unit:
        if index < len(raw_text) and raw_text[index] == " ":
            index += 1
        if index >= len(raw_text) or not raw_text.startswith(unit, index):
            return None
        span_end = index + len(unit)
    else:
        span_end = index
        
    span = SourceSpan(start, span_end)
    if not _valid_boundaries(raw_text, span, unit):
        return None
    return span


def _parse_signed_surface(raw: str) -> tuple[str, str, str] | None:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    if len(raw) < 2 or not is_signed_numeric_sign(raw[0]):
        return None
    sign, unsigned_raw = strip_signed_numeric_sign(raw)
    if sign is None:
        return None
    
    temperature_unit = _signed_temperature_unit_suffix(raw)
    if temperature_unit is not None:
        unit = temperature_unit
        numeric = unsigned_raw[: -len(unit)]
    elif raw[-1] in _BARE_DEGREE_UNITS:
        unit = raw[-1]
        numeric = unsigned_raw[:-1]
    else:
        unit = ""
        numeric = unsigned_raw
        
    if parse_signed_numeric(numeric) is None:
        return None
    return sign, numeric, unit


def _signed_temperature_unit_suffix(raw: str) -> str | None:
    for unit in _SIGNED_TEMPERATURE_UNITS:
        if raw.endswith(unit):
            return unit
    return None


def _has_matching_temperature_label_context(raw_text: str, start: int, unit: str) -> bool:
    label = _matching_temperature_label(unit)
    if label is None:
        return False
    left = raw_text[:start].rstrip(" ")
    if not left.endswith(label):
        return False
    label_start = len(left) - len(label)
    prev_char = left[label_start - 1] if label_start > 0 else None
    if prev_char is None:
        return True
    if "\uac00" <= prev_char <= "\ud7a3":
        return False
    if prev_char.isascii() and prev_char.isalnum():
        return False
    return True


def _matching_temperature_label(unit: str) -> str | None:
    if unit in _FAHRENHEIT_UNITS:
        return "화씨"
    if unit in _CELSIUS_UNITS:
        return "섭씨"
    return None


def _consume_digits_and_commas(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        if _is_ascii_digit(raw_text[index]):
            index += 1
        elif raw_text[index] == ",":
            if index + 3 < len(raw_text) and _is_ascii_digits(raw_text[index+1:index+4]) and (index + 4 == len(raw_text) or not _is_ascii_digit(raw_text[index+4])):
                index += 4
            else:
                break
        else:
            break
    return index


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _is_blocked_start(raw_text: str, start: int, owner: str) -> bool:
    if start == 0:
        return False
    prev_char = raw_text[start - 1]
    if prev_char.isspace():
        return False
    if prev_char in {"(", "[", "{", '"', "'"}:
        return False
    if prev_char == ")" and _has_textual_parenthesized_prefix(raw_text, start):
        return True
    if "\uac00" <= prev_char <= "\ud7a3":
        return owner not in {"signed_temperature", "signed_degree"}
    # If the previous character is alphabetic, do not parse as a plain signed number. (e.g. B-2.5, 코드A-3)
    if prev_char.isascii() and prev_char.isalpha():
        return True
    return (
        (prev_char.isascii() and prev_char.isalnum())
        or ("\u3130" <= prev_char <= "\u318f")
        or (prev_char in SIGNED_NUMERIC_SIGN_ALIASES | {".", "_", "/", "℃", "℉", "°", ","})
    )


def _has_textual_parenthesized_prefix(raw_text: str, sign_start: int) -> bool:
    """Reject a sign after ``영문(한글)`` or ``한글(한글)`` as unary minus."""
    close_index = sign_start - 1
    open_index = raw_text.rfind("(", 0, close_index)
    if open_index <= 0:
        return False
    alias = raw_text[open_index + 1 : close_index]
    if not alias or not all(_is_hangul_syllable(char) for char in alias):
        return False
    prefix = raw_text[open_index - 1]
    return _is_hangul_syllable(prefix) or (prefix.isascii() and prefix.isalpha())


def _valid_boundaries(raw_text: str, span: SourceSpan, unit: str) -> bool:
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_non_space = raw_text[span.end :].lstrip()
    if prev_char is not None and not (
        prev_char.isspace() or prev_char in {"(", "[", "{", '"', "'"}
    ):
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            if not unit:
                return False
        elif "\u3130" <= prev_char <= "\u318f":
            return False
        if prev_char in SIGNED_NUMERIC_SIGN_ALIASES | {".", "_", "/", "℃", "℉", "°"}:
            return False
        if prev_char == ",":
            if span.start > 1 and _is_ascii_digit(raw_text[span.start - 2]):
                return False
    if next_char is None:
        return True
    if not unit and next_char.isspace() and starts_with_supported_unit(next_non_space):
        return False
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char == ".":
        next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
        if next_next is not None and _is_ascii_digit(next_next):
            return False
    elif next_char in SIGNED_NUMERIC_SIGN_ALIASES | {"_", "/", "℃", "℉", "°"}:
        return False
    if next_char == ",":
        if span.end + 1 < len(raw_text) and _is_ascii_digit(raw_text[span.end + 1]):
            return False
    
    # Do not parse signed number if it's followed by a colon (e.g. 3:-2, 3:2)
    # But for a signed number owner, maybe we just block next_char == ':'
    if not unit and next_char == ":":
        return False
        
    return True


def _is_valid_signed_temperature_surface(
    raw_text: str, start: int, span: SourceSpan
) -> bool:
    if _parse_signed_surface(raw_text[start : span.end]) is None:
        return False
    if _is_blocked_start(raw_text, start, "signed_temperature"):
        return False
    if not _valid_boundaries(raw_text, span, "temperature"):
        return False
    return _signed_temperature_degree_tail_is_allowed(raw_text[span.end :])


def _is_valid_signed_degree_surface(raw_text: str, start: int, span: SourceSpan) -> bool:
    if _parse_signed_surface(raw_text[start : span.end]) is None:
        return False
    if _is_blocked_start(raw_text, start, "signed_degree"):
        return False
    if not _valid_boundaries(raw_text, span, "degree"):
        return False
    return _signed_temperature_degree_tail_is_allowed(raw_text[span.end :])


def _signed_span_is_decimal(raw_text: str, span: SourceSpan) -> bool:
    return "." in raw_text[span.start : span.end]


def _tail_starts_with_registered_numeric_suffix(tail: str) -> bool:
    return any(tail.startswith(suffix) for suffix in ("분기", "시리즈"))


def _tail_is_allowed_for_owner(tail: str, owner: str) -> bool:
    if owner in {"signed_temperature", "signed_degree"}:
        return _signed_temperature_degree_tail_is_allowed(tail)
    if owner == "signed_number":
        return _signed_number_tail_is_allowed(tail)
    return _tail_is_allowed(tail)


def _signed_number_tail_is_allowed(tail: str) -> bool:
    if _tail_is_allowed(tail):
        return True
    if not tail or not _is_hangul_syllable(tail[0]):
        return False
    for prefix in _registered_hangul_numeric_prefixes():
        if not tail.startswith(prefix):
            continue
        return _tail_is_allowed(tail[len(prefix) :])
    return True


def _registered_hangul_numeric_prefixes() -> tuple[str, ...]:
    from engine.span_engine.counter import COUNTERS_BY_LENGTH

    return tuple(
        sorted(
            set(COUNTERS_BY_LENGTH) | _CONTEXTUAL_HANGUL_NUMERIC_UNITS,
            key=len,
            reverse=True,
        )
    )


def _tail_is_allowed(tail: str) -> bool:
    if tail == "":
        return True
    if tail[0].isspace():
        return True
    if tail[0] in _TAIL_PUNCTUATION:
        return True
    for allowed in (value for value in _ALLOWED_TAILS if value):
        if tail.startswith(allowed):
            return True
    return False


def _signed_temperature_degree_tail_is_allowed(tail: str) -> bool:
    if tail == "":
        return True
    if tail[0].isspace():
        return True
    if tail[0] in _TAIL_PUNCTUATION:
        return True
    if _is_hangul_syllable(tail[0]):
        return True
    return False


def _is_hangul_syllable(ch: str) -> bool:
    return "\uac00" <= ch <= "\ud7a3"


def _tail_prefix(tail: str) -> str | None:
    for allowed in sorted(_ALLOWED_TAILS, key=len, reverse=True):
        if allowed and tail.startswith(allowed):
            return allowed
    return "" if tail == "" else None


def _span_overlaps_excluded_range(
    span: SourceSpan, excluded_ranges: list[BracketRange]
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "parse_signed_candidate",
    "parse_signed_numeric",
    "scan_compound_signed_number_candidates",
    "scan_invalid_signed_numeric_preserve_candidates",
    "scan_signed_degree_candidates",
    "scan_signed_number_candidates",
    "scan_signed_temperature_candidates",
    "signed_degree_reading",
    "signed_temperature_reading",
]
