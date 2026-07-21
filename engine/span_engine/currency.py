from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from engine.span_engine.amount_reading import read_decimal_amount_text
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.numeric_reading import read_decimal_fraction_digits
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    apply_sign_profile,
    parse_signed_numeric_core,
)

CURRENCY_SYMBOL_READINGS: dict[str, str] = {
    "$": "달러",
    "＄": "달러",
    "﹩": "달러",
    "€": "유로",
    "₩": "원",
    "￦": "원",
    "¥": "엔",
    "￥": "엔",
    "£": "파운드",
}

CURRENCY_CODE_READINGS: dict[str, str] = {
    "USD": "달러",
    "EUR": "유로",
    "KRW": "원",
    "JPY": "엔",
    "GBP": "파운드",
}

KOREAN_CURRENCY_SUFFIX_READINGS: dict[str, str] = {
    "원": "원",
    "달러": "달러",
    "유로": "유로",
    "엔": "엔",
}

PREFIX_CURRENCY_MARKER_READINGS: dict[str, str] = {
    **CURRENCY_SYMBOL_READINGS,
    **CURRENCY_CODE_READINGS,
}

SUFFIX_CURRENCY_MARKER_READINGS: dict[str, str] = {
    **CURRENCY_SYMBOL_READINGS,
    **CURRENCY_CODE_READINGS,
    **KOREAN_CURRENCY_SUFFIX_READINGS,
}

CURRENCY_CODE_BLOCKLIST = frozenset(
    {
        "AUD",
        "BTC",
        "CAD",
        "CHF",
        "CNY",
        "GBP",
        "EUR",
        "JPY",
        "KRW",
        "SGD",
        "USD",
        "US",
    }
)

DECIMAL_ALLOWED_CURRENCIES = frozenset({"달러", "유로"})
COMMA_INTEGER_ALLOWED_CURRENCIES = frozenset({"원", "엔", "유로"})
_AMOUNT_RE = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_UNSUPPORTED_CODE_AMOUNT_RE = re.compile(
    rf"(?<![A-Za-z0-9])([A-Z]{{2,}}) ?({_AMOUNT_RE.pattern})(?![A-Za-z0-9_.])"
)
_KOREAN_CURRENCY_TRAILING_PARTICLES = ("은", "는", "이", "가", "을", "를", "와", "과", "도")
_PREFIX_MARKERS_BY_LENGTH = sorted(PREFIX_CURRENCY_MARKER_READINGS, key=len, reverse=True)
_SUFFIX_MARKERS_BY_LENGTH = sorted(SUFFIX_CURRENCY_MARKER_READINGS, key=len, reverse=True)
_SIGN_CHARS = frozenset({"+", "-"})


def scan_currency_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    candidates: list[SurfaceCandidate] = []
    candidates.extend(_scan_unsupported_currency_code_amount(raw_text))
    candidates.extend(_scan_large_unit_currency(raw_text))
    candidates.extend(_scan_decimal_large_unit_krw(raw_text))
    candidates.extend(_scan_symbol_currency(raw_text))
    candidates.extend(_scan_code_currency(raw_text))
    candidates.extend(_scan_suffix_currency(raw_text))
    candidates.extend(_scan_invalid_currency_contexts(raw_text))
    return sorted(candidates, key=lambda candidate: candidate.core_span.start)


def parse_currency_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "currency":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        return reading
    raw = raw_text[candidate.core_span.start : candidate.core_span.end]
    parsed = _parse_currency_surface(raw)
    return parsed[2] if parsed is not None else None


def is_currency_like_code(raw: str) -> bool:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    return raw in CURRENCY_CODE_BLOCKLIST


def is_currency_code_contaminated_token(raw: str) -> bool:
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    if not raw.isascii() or not raw.isalpha():
        return False
    return any(
        raw.startswith(code) and raw != code for code in CURRENCY_CODE_READINGS
    )


def is_number_after_unsupported_currency_code(raw_text: str, start: int) -> bool:
    prefix = raw_text[:start].rstrip()
    if not prefix:
        return False
    token_start = len(prefix)
    while token_start > 0 and prefix[token_start - 1].isalpha():
        token_start -= 1
    token = prefix[token_start:]
    if is_currency_code_contaminated_token(token):
        return True
    return token in CURRENCY_CODE_BLOCKLIST and token not in CURRENCY_CODE_READINGS


def _scan_unsupported_currency_code_amount(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _UNSUPPORTED_CODE_AMOUNT_RE.finditer(raw_text):
        code = match.group(1)
        if code in CURRENCY_CODE_READINGS:
            continue
        if not (
            is_currency_code_contaminated_token(code)
            or code in CURRENCY_CODE_BLOCKLIST
        ):
            continue
        span = SourceSpan(match.start(), match.end())
        candidates.append(
            _preserve_candidate(span, "unsupported_currency_code_amount_preserve")
        )
    return candidates


def _scan_symbol_currency(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for index, char in enumerate(raw_text):
        currency_name = CURRENCY_SYMBOL_READINGS.get(char)
        if currency_name is not None:
            candidate = _prefix_marker_candidate(
                raw_text,
                index,
                char,
                currency_name,
                "currency_symbol_with_amount",
            )
            if candidate is not None:
                candidates.append(candidate)
            continue
        if char not in _SIGN_CHARS:
            continue
        marker_start = index + 1
        marker = _prefix_marker_at(raw_text, marker_start, symbols_only=True)
        if marker is None:
            continue
        marker_end, _, currency_name = marker
        candidate = _signed_prefix_symbol_candidate(
            raw_text,
            index,
            marker_end,
            char,
            currency_name,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _scan_code_currency(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for index in range(len(raw_text)):
        for code, currency_name in CURRENCY_CODE_READINGS.items():
            candidate = _prefix_marker_candidate(
                raw_text,
                index,
                code,
                currency_name,
                "currency_code_with_amount",
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _scan_suffix_currency(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    for match in _AMOUNT_RE.finditer(raw_text):
        amount = match.group(0)
        amount_start = match.start()
        amount_end = match.end()
        signed_amount_start = amount_start
        if amount_start > 0 and raw_text[amount_start - 1] in _SIGN_CHARS:
            signed_amount_start = amount_start - 1
            amount = raw_text[amount_start - 1] + amount
        if amount_start > 0:
            prev_char = raw_text[amount_start - 1]
            prev_prev = raw_text[amount_start - 2] if amount_start > 1 else None
            if prev_char in _SIGN_CHARS:
                if prev_prev is not None and (
                    (prev_prev.isascii() and prev_prev.isalnum())
                    or prev_prev in {"_", "/", ".", "+", "-"}
                    or prev_prev in CURRENCY_SYMBOL_READINGS
                ):
                    continue
            elif prev_char.isascii() and prev_char.isalnum():
                continue
            elif "\uac00" <= prev_char <= "\ud7a3":
                continue
            elif prev_char == ",":
                continue
            elif prev_char in {"_", "/", "."}:
                continue
            elif prev_char in CURRENCY_SYMBOL_READINGS:
                continue
        gap_end, gap = _consume_currency_gap(raw_text, amount_end)
        if gap not in {"", " "}:
            continue
        suffix = _suffix_currency_at(raw_text, gap_end)
        if suffix is None:
            continue
        suffix_end, currency_name = suffix
        suffix_raw = raw_text[gap_end:suffix_end]
        if suffix_raw in KOREAN_CURRENCY_SUFFIX_READINGS:
            candidate = _korean_suffix_candidate(
                raw_text,
                signed_amount_start,
                amount_end,
                gap_end,
                suffix_end,
                amount,
                currency_name,
            )
            if candidate is not None:
                candidates.append(candidate)
            continue
        span = SourceSpan(signed_amount_start, suffix_end)
        if not _amount_allowed_for_currency(amount, currency_name):
            candidates.append(_preserve_candidate(span, "currency_amount_policy_preserve"))
            continue
        if not _valid_amount_and_boundary(raw_text, span, amount):
            candidates.append(
                _preserve_candidate(
                    SourceSpan(signed_amount_start, _currency_like_token_end(raw_text, suffix_end)),
                    "currency_invalid_tail_preserve",
                )
            )
            continue
        candidates.append(
            _candidate(
                span=span,
                amount=amount,
                currency_name=currency_name,
                reason="currency_suffix_with_amount",
            )
        )
    return candidates


def _prefix_marker_candidate(
    raw_text: str,
    index: int,
    marker: str,
    currency_name: str,
    reason: str,
) -> SurfaceCandidate | None:
    if not raw_text.startswith(marker, index):
        return None
    if not _valid_currency_left_boundary(raw_text, index):
        return None
    if _is_range_left_context(raw_text, index):
        return None
    marker_end = index + len(marker)
    amount_start, gap = _consume_currency_gap(raw_text, marker_end)
    if gap not in {"", " "}:
        return None
    parsed = _parse_amount_at(raw_text, amount_start)
    if parsed is None:
        return None
    amount, amount_end = parsed
    span = SourceSpan(index, amount_end)
    if not _amount_allowed_for_currency(amount, currency_name):
        return _preserve_candidate(span, "currency_amount_policy_preserve")
    if not _valid_amount_and_boundary(raw_text, span, amount):
        return _preserve_candidate(
            SourceSpan(index, _currency_like_token_end(raw_text, amount_end)),
            "currency_invalid_tail_preserve",
        )
    return _candidate(
        span=span,
        amount=amount,
        currency_name=currency_name,
        reason=reason,
    )


def _signed_prefix_symbol_candidate(
    raw_text: str,
    sign_start: int,
    marker_end: int,
    sign: str,
    currency_name: str,
) -> SurfaceCandidate | None:
    if not _valid_currency_left_boundary(raw_text, sign_start):
        return None
    if _is_range_left_context(raw_text, sign_start):
        return None
    amount_start, gap = _consume_currency_gap(raw_text, marker_end)
    if gap not in {"", " "}:
        return None
    parsed = _parse_unsigned_amount_at(raw_text, amount_start)
    if parsed is None:
        return None
    unsigned_amount, amount_end = parsed
    amount = sign + unsigned_amount
    span = SourceSpan(sign_start, amount_end)
    if not _amount_allowed_for_currency(amount, currency_name):
        return _preserve_candidate(span, "currency_amount_policy_preserve")
    if not _valid_amount_and_boundary(raw_text, span, amount):
        return _preserve_candidate(
            SourceSpan(sign_start, _currency_like_token_end(raw_text, amount_end)),
            "currency_invalid_tail_preserve",
        )
    return _candidate(
        span=span,
        amount=amount,
        currency_name=currency_name,
        reason="signed_currency_symbol_with_amount",
    )


def _scan_invalid_currency_contexts(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    candidates.extend(_scan_invalid_prefix_currency_contexts(raw_text))
    candidates.extend(_scan_invalid_signed_prefix_symbol_contexts(raw_text))
    candidates.extend(_scan_invalid_suffix_currency_contexts(raw_text))
    return candidates


def _scan_invalid_prefix_currency_contexts(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        marker = _prefix_marker_at(raw_text, index)
        if marker is None:
            index += 1
            continue
        marker_end, marker_raw, currency_name = marker
        if not _valid_currency_left_boundary(raw_text, index):
            index += 1
            continue
        if _is_range_left_context(raw_text, index):
            index += 1
            continue
        amount_start, gap = _consume_currency_gap(raw_text, marker_end)
        amount_end = _consume_currency_amount_like(raw_text, amount_start)
        if amount_end is None:
            index += 1
            continue
        amount = raw_text[amount_start:amount_end]
        span = SourceSpan(index, amount_end)
        if (
            gap in {"", " "}
            and _amount_allowed_for_currency(amount, currency_name)
            and _valid_amount_and_boundary(raw_text, span, amount)
        ):
            index += 1
            continue
        candidates.append(
            _preserve_candidate(
                SourceSpan(index, _currency_like_token_end(raw_text, amount_end)),
                "currency_invalid_numeric_or_spacing_preserve",
            )
        )
        index = amount_end
    return candidates


def _scan_invalid_signed_prefix_symbol_contexts(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if raw_text[index] not in _SIGN_CHARS:
            index += 1
            continue
        marker_start = index + 1
        while marker_start < len(raw_text) and raw_text[marker_start] in _SIGN_CHARS:
            marker_start += 1
        marker = _prefix_marker_at(raw_text, marker_start, symbols_only=True)
        if marker is None:
            index += 1
            continue
        marker_end, _, currency_name = marker
        amount_start, gap = _consume_currency_gap(raw_text, marker_end)
        amount_end = _consume_currency_amount_like(raw_text, amount_start)
        if amount_end is None:
            index += 1
            continue
        amount = raw_text[index] + raw_text[amount_start:amount_end]
        span = SourceSpan(index, amount_end)
        if (
            marker_start == index + 1
            and gap in {"", " "}
            and _amount_allowed_for_currency(amount, currency_name)
            and _valid_amount_and_boundary(raw_text, span, amount)
        ):
            index += 1
            continue
        candidates.append(
            _preserve_candidate(
                SourceSpan(index, _currency_like_token_end(raw_text, amount_end)),
                "currency_invalid_numeric_or_spacing_preserve",
            )
        )
        index = amount_end
    return candidates


def _scan_invalid_suffix_currency_contexts(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not (
            _is_ascii_digit(raw_text[index])
            or raw_text[index] == "."
            or raw_text[index] in _SIGN_CHARS
        ):
            index += 1
            continue
        if raw_text[index] not in _SIGN_CHARS and index > 0 and raw_text[index - 1] in _SIGN_CHARS:
            index += 1
            continue
        if index > 0 and raw_text[index - 1] in {",", "."}:
            index += 1
            continue
        if not _valid_currency_left_boundary(raw_text, index):
            index += 1
            continue
        if _is_range_left_context(raw_text, index):
            index += 1
            continue
        amount_end = _consume_currency_amount_like(raw_text, index)
        if amount_end is None:
            index += 1
            continue
        suffix_start, gap = _consume_currency_gap(raw_text, amount_end)
        suffix = _suffix_currency_at(raw_text, suffix_start)
        if suffix is None:
            index += 1
            continue
        suffix_end, currency_name = suffix
        amount = raw_text[index:amount_end]
        span = SourceSpan(index, suffix_end)
        if (
            gap in {"", " "}
            and _amount_allowed_for_currency(amount, currency_name)
            and _valid_amount_and_boundary(raw_text, span, amount)
        ):
            index += 1
            continue
        candidates.append(
            _preserve_candidate(
                SourceSpan(index, _currency_like_token_end(raw_text, suffix_end)),
                "currency_invalid_numeric_or_spacing_preserve",
            )
        )
        index = suffix_end
    return candidates


def _scan_large_unit_currency(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    number = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    pattern = re.compile(
        rf"(?<![A-Za-z0-9가-힣_])({number}[만억조](?: {number}[만억조])*) ?(원|달러|유로|엔)"
    )
    for match in pattern.finditer(raw_text):
        body = match.group(1)
        currency = match.group(2)
        if not _valid_large_unit_currency_boundary(raw_text, match.end()):
            continue
        if "," not in body:
            continue
        reading = _large_unit_body_reading(body)
        if reading is None:
            continue
        if match.end(1) == match.start(2):
            reading = f"{reading} {currency}"
            span = SourceSpan(match.start(), match.end())
        else:
            span = SourceSpan(match.start(), match.end(1))
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=SourceSpan(match.start(), match.end()),
                owner="currency",
                surface_type="CURRENCY_SURFACE",
                reason="large_unit_currency_suffix",
                metadata={
                    "currency": currency,
                    "reading": reading,
                },
            )
        )
    return candidates


def _valid_large_unit_currency_boundary(raw_text: str, end: int) -> bool:
    if end >= len(raw_text):
        return True
    next_char = raw_text[end]
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char == "_":
        return False
    if "\uac00" <= next_char <= "\ud7a3":
        return raw_text.startswith(_KOREAN_CURRENCY_TRAILING_PARTICLES, end)
    return True


def _parse_currency_surface(raw: str) -> tuple[str, str, str] | None:
    for symbol, currency_name in CURRENCY_SYMBOL_READINGS.items():
        if raw.startswith(symbol):
            amount = raw[len(symbol) :].strip()
            if _is_supported_amount(amount, currency_name):
                return amount, currency_name, _reading(amount, currency_name)
    for code, currency_name in CURRENCY_CODE_READINGS.items():
        if raw.startswith(code):
            amount = raw[len(code) :].strip()
            if _is_supported_amount(amount, currency_name):
                return amount, currency_name, _reading(amount, currency_name)
    return None


def _candidate(
    span: SourceSpan, amount: str, currency_name: str, reason: str
) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="currency",
        surface_type="CURRENCY_SURFACE",
        reason=reason,
        metadata={
            "amount": amount,
            "currency": currency_name,
            "reading": _reading(amount, currency_name),
            **_signed_contract_metadata(amount),
        },
    )


def _korean_suffix_candidate(
    raw_text: str,
    amount_start: int,
    amount_end: int,
    suffix_start: int,
    suffix_end: int,
    amount: str,
    currency_name: str,
) -> SurfaceCandidate | None:
    if not _amount_allowed_for_currency(amount, currency_name):
        return None
    validation_span = SourceSpan(amount_start, suffix_end)
    if not _valid_amount_and_boundary(raw_text, validation_span, amount):
        return None
    reading = _korean_suffix_amount_reading(amount, currency_name)
    if suffix_start == amount_end:
        reading += " "
    span = SourceSpan(amount_start, amount_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="currency",
        surface_type="CURRENCY_SURFACE",
        reason="korean_currency_suffix_amount_with_registered_marker",
        metadata={
            "amount": amount,
            "currency": currency_name,
            "reading": reading,
            **_signed_contract_metadata(amount),
        },
    )


def _reading(amount: str, currency_name: str) -> str:
    return f"{_amount_reading(amount, currency_name)} {currency_name}"


def _signed_contract_metadata(amount: str) -> dict[str, object]:
    policy = SIGNED_OWNER_POLICIES["currency"]
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


def _amount_reading(amount: str, currency_name: str) -> str:
    policy = SIGNED_OWNER_POLICIES["currency"]
    core = parse_signed_numeric_core(
        amount,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
        numeric_forms=policy.numeric_forms,
    )
    if core is None:
        raise ValueError("invalid currency amount")
    if currency_name == "원":
        reading = _krw_amount_reading(core.number.raw)
    else:
        reading = read_decimal_amount_text(
            core.number.raw,
            overflow_message="currency amount must be below 100000000",
        )
    signed_reading = apply_sign_profile(
        reading,
        core.sign_kind,
        sign_profile=policy.sign_profile,
    )
    if signed_reading is None:
        raise ValueError("currency owner rejects numeric sign")
    return signed_reading


def _korean_suffix_amount_reading(amount: str, currency_name: str) -> str:
    return _amount_reading(amount, currency_name)


def _krw_amount_reading(amount: str) -> str:
    integer_part, dot, fractional_part = amount.partition(".")
    integer_reading = read_decimal_amount_text(
        integer_part,
        overflow_message="currency amount must be below 100000000",
    )
    if not dot:
        return integer_reading
    fractional = read_decimal_fraction_digits(fractional_part)
    return f"{integer_reading}쩜{fractional}"


def _unsigned_amount(amount: str) -> str | None:
    if amount.startswith(("+", "-")):
        unsigned = amount[1:]
        return unsigned if unsigned else None
    return amount


def _large_unit_body_reading(body: str) -> str | None:
    chunk_pattern = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)([만억조])")
    cursor = 0
    previous_rank = 4
    parts: list[str] = []
    ranks = {"조": 3, "억": 2, "만": 1}
    for match in chunk_pattern.finditer(body):
        if match.start() != cursor:
            return None
        amount = match.group(1)
        unit = match.group(2)
        if not _amount_shape_valid(amount):
            return None
        normalized = amount.replace(",", "")
        value = int(normalized)
        if value <= 0 or value > 9999:
            return None
        rank = ranks[unit]
        if rank >= previous_rank:
            return None
        parts.append(f"{number_to_korean_under_10000(value)}{unit}")
        cursor = match.end()
        if cursor < len(body) and body[cursor] == " ":
            cursor += 1
        previous_rank = rank
    if cursor != len(body) or not parts:
        return None
    return " ".join(parts)


def _scan_decimal_large_unit_krw(raw_text: str) -> list[SurfaceCandidate]:
    candidates: list[SurfaceCandidate] = []
    pattern = re.compile(r"(?<![A-Za-z0-9가-힣])(\d+\.\d+)([만억조]) ?원(?![A-Za-z0-9가-힣])")
    for match in pattern.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        amount = match.group(1)
        large_unit = match.group(2)
        expanded = _expanded_krw_amount(amount, large_unit)
        if expanded is None:
            continue
        core_span = SourceSpan(match.start(), match.end(2))
        candidates.append(
            SurfaceCandidate(
                core_span=core_span,
                full_span=span,
                owner="currency",
                surface_type="CURRENCY_SURFACE",
                reason="decimal_large_unit_krw_expansion",
                metadata={
                    "amount": amount,
                    "currency": "원",
                    "large_unit": large_unit,
                    "reading": _spaced_large_integer_reading(expanded),
                },
            )
        )
    return candidates


def _expanded_krw_amount(amount: str, large_unit: str) -> int | None:
    multipliers = {"만": 10_000, "억": 100_000_000, "조": 1_000_000_000_000}
    multiplier = multipliers.get(large_unit)
    if multiplier is None:
        return None
    try:
        value = Decimal(amount) * Decimal(multiplier)
    except InvalidOperation:
        return None
    if value <= 0 or value != value.to_integral_value():
        return None
    expanded = int(value)
    if expanded >= 10 ** 16:
        return None
    return expanded


def _spaced_large_integer_reading(value: int) -> str:
    if value == 0:
        return "영"
    units = ["", "만", "억", "조"]
    groups: list[int] = []
    remaining = value
    while remaining:
        groups.append(remaining % 10000)
        remaining //= 10000
    parts: list[str] = []
    for index in range(len(groups) - 1, -1, -1):
        group_value = groups[index]
        if group_value == 0:
            continue
        unit = units[index]
        group_reading = number_to_korean_under_10000(group_value)
        if unit == "만" and group_reading == "일":
            parts.append(unit)
        else:
            parts.append(f"{group_reading}{unit}")
    return " ".join(parts)


def _parse_amount_at(raw_text: str, start: int) -> tuple[str, int] | None:
    match = _AMOUNT_RE.match(raw_text, start)
    if match is None:
        return None
    amount = match.group(0)
    if not _amount_shape_valid(amount):
        return None
    return amount, match.end()


def _parse_unsigned_amount_at(raw_text: str, start: int) -> tuple[str, int] | None:
    parsed = _parse_amount_at(raw_text, start)
    if parsed is None:
        return None
    amount, amount_end = parsed
    if amount.startswith(("+", "-")):
        return None
    return amount, amount_end


def _consume_optional_ascii_space(raw_text: str, start: int) -> int:
    if start < len(raw_text) and raw_text[start] == " ":
        return start + 1
    return start


def _consume_currency_gap(raw_text: str, start: int) -> tuple[int, str]:
    index = start
    while index < len(raw_text) and raw_text[index].isspace():
        index += 1
    return index, raw_text[start:index]


def _is_supported_amount(amount: str, currency_name: str) -> bool:
    return _amount_allowed_for_currency(amount, currency_name) and _amount_shape_valid(amount)


def _amount_allowed_for_currency(amount: str, currency_name: str) -> bool:
    unsigned = _unsigned_amount(amount)
    if unsigned is None:
        return False
    return _amount_shape_valid(unsigned)


def _amount_shape_valid(amount: str) -> bool:
    unsigned = _unsigned_amount(amount)
    if unsigned is None:
        return False
    amount = unsigned
    integer_part, _, decimal_part = amount.partition(".")
    if "." in amount and decimal_part == "":
        return False
    digits = integer_part.replace(",", "")
    if not digits:
        return False
    if "," not in integer_part and len(digits) > 1 and digits.startswith("0"):
        return False
    if "," in integer_part:
        groups = integer_part.split(",")
        if not 1 <= len(groups[0]) <= 3:
            return False
        if not all(group.isdigit() for group in groups):
            return False
        if len(groups[0]) > 1 and groups[0].startswith("0"):
            return False
        if any(len(group) != 3 for group in groups[1:]):
            return False
    if decimal_part and not decimal_part.isdigit():
        return False
    return int(digits) < 100000000


def _consume_currency_amount_like(raw_text: str, start: int) -> int | None:
    index = start
    while index < len(raw_text) and raw_text[index] in _SIGN_CHARS:
        index += 1
    numeric_start = index
    saw_digit = False
    while index < len(raw_text):
        char = raw_text[index]
        if _is_ascii_digit(char):
            saw_digit = True
            index += 1
            continue
        if char == ",":
            if index + 1 >= len(raw_text) or not _is_ascii_digit(raw_text[index + 1]):
                break
            index += 1
            continue
        if char == ".":
            index += 1
            continue
        break
    if index == numeric_start:
        if index < len(raw_text) and raw_text[index] == ".":
            index += 1
            while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
                saw_digit = True
                index += 1
        if not saw_digit:
            return None
    return index if saw_digit else None


def _prefix_marker_at(
    raw_text: str, start: int, *, symbols_only: bool = False
) -> tuple[int, str, str] | None:
    readings = CURRENCY_SYMBOL_READINGS if symbols_only else PREFIX_CURRENCY_MARKER_READINGS
    markers = sorted(readings, key=len, reverse=True)
    for marker in markers:
        if raw_text.startswith(marker, start):
            return start + len(marker), marker, readings[marker]
    return None


def _valid_currency_left_boundary(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    if prev_char is None:
        return True
    if prev_char.isspace():
        return True
    if prev_char in {"(", "[", "{", '"', "'"}:
        return True
    if prev_char.isascii() and prev_char.isalnum():
        return False
    if "\uac00" <= prev_char <= "\ud7a3" or "\u3130" <= prev_char <= "\u318f":
        return False
    return prev_char not in {"_", "/", "."}


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _valid_amount_and_boundary(raw_text: str, span: SourceSpan, amount: str) -> bool:
    if not _amount_shape_valid(amount):
        return False
    if not _valid_currency_left_boundary(raw_text, span.start):
        return False
    prev_char = raw_text[span.start - 1] if span.start > 0 else None
    next_char = raw_text[span.end] if span.end < len(raw_text) else None
    next_next = raw_text[span.end + 1] if span.end + 1 < len(raw_text) else None
    if prev_char is not None and prev_char in {"~", "∼", "〜", "～", "-", "–"}:
        return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in {"+", "-", "~", ":", "/", "%"}:
        return False
    # A trailing comma is a list separator (e.g. "$25.99, €1,234"), not part of
    # the amount.  Block only if the comma is followed by a digit (which would
    # indicate the comma is inside a number like "1,234" that was already
    # consumed by _parse_amount_at).
    if next_char == ",":
        return not (next_next is not None and next_next.isdigit())
    if next_char == ".":
        return _span_ends_with_registered_currency_marker(raw_text, span)
    return True


def _is_range_left_context(raw_text: str, start: int) -> bool:
    prev_char = raw_text[start - 1] if start > 0 else None
    return prev_char in {"~", "∼", "〜", "～", "-", "–"}


def _span_ends_with_registered_currency_marker(raw_text: str, span: SourceSpan) -> bool:
    raw = raw_text[span.start : span.end]
    return any(raw.endswith(marker) for marker in SUFFIX_CURRENCY_MARKER_READINGS)


def _suffix_currency_at(raw_text: str, start: int) -> tuple[int, str] | None:
    char = raw_text[start : start + 1]
    if char in CURRENCY_SYMBOL_READINGS:
        return start + 1, CURRENCY_SYMBOL_READINGS[char]
    for suffix, currency_name in KOREAN_CURRENCY_SUFFIX_READINGS.items():
        if raw_text.startswith(suffix, start):
            return start + len(suffix), currency_name
    for code, currency_name in CURRENCY_CODE_READINGS.items():
        if raw_text.startswith(code, start):
            return start + len(code), currency_name
    return None


def _currency_like_token_end(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text):
        char = raw_text[index]
        if char.isascii() and char.isalnum():
            index += 1
            continue
        if char in {".", ",", "_"}:
            index += 1
            continue
        break
    return index


def _preserve_candidate(span: SourceSpan, reason: str) -> SurfaceCandidate:
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="CURRENCY_PRESERVE_SURFACE",
        reason=reason,
    )


__all__ = [
    "CURRENCY_CODE_BLOCKLIST",
    "CURRENCY_CODE_READINGS",
    "CURRENCY_SYMBOL_READINGS",
    "KOREAN_CURRENCY_SUFFIX_READINGS",
    "is_currency_code_contaminated_token",
    "is_currency_like_code",
    "is_number_after_unsupported_currency_code",
    "parse_currency_candidate",
    "scan_currency_candidates",
]
