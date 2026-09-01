from __future__ import annotations

from dataclasses import dataclass

from engine.span_engine.models import RenderPiece
from engine.span_engine.models import SourceSpan, SurfaceCandidate
from engine.span_engine.number import number_to_korean_under_10000
from engine.span_engine.numeric_prosody import join_decimal_prosody
from engine.span_engine.numeric_reading import read_decimal_fraction_digits
from engine.span_engine.signed import parse_signed_numeric
from engine.span_engine.signed_numeric import (
    SIGNED_OWNER_POLICIES,
    render_signed_numeric,
    parse_signed_numeric_core,
)
from engine.span_engine.spoken_boundary import SPOKEN_NUMERIC_BOUNDARY

LARGE_UNIT_ATOMIC_INVENTORY = frozenset({"만", "억", "조", "경"})
_AMBIGUOUS_SUFFIX_PREFIXES = ("개",)
_PREV_BLOCKERS = frozenset("+-.,~:/_")
_NEXT_BLOCKERS = frozenset("+-.,~:/_")
_UNSAFE_FOLLOWING_DELIMITERS = frozenset(
    {"–", "—", "−", "－", "＋", "·"}
)
_SAFE_RIGHT_PUNCTUATION = frozenset(",.!?)]};:")
_LARGE_UNIT_SIGNS = frozenset({"+", "-"})
_SMALL_UNITS = {"천": 1000, "백": 100, "십": 10}
_SMALL_UNIT_ORDER = {"천": 3, "백": 2, "십": 1}
_LARGE_UNIT_ORDER = {"만": 1, "억": 2, "조": 3, "경": 4}
_LARGE_UNIT_VALUES = {
    "만": 10_000,
    "억": 100_000_000,
    "조": 1_000_000_000_000,
    "경": 10_000_000_000_000_000,
}
_ATTACHED_HANGUL_TAILS = (
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
_TOKEN_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_,.+-")


@dataclass(frozen=True)
class _LargeUnitParse:
    core_span: SourceSpan
    numeric_span: SourceSpan
    suffix_span: SourceSpan
    reading: str
    has_decimal: bool
    reason: str
    reading_includes_suffix: bool = False
    render_parts: tuple[tuple[SourceSpan, str, str], ...] = ()
    sign_profile: str | None = None
    numeric_form: str | None = None
    sign_surface: str | None = None
    integer_value: int | None = None


def is_large_unit(ch: str) -> bool:
    if not isinstance(ch, str):
        raise TypeError("ch must be str")
    return ch in LARGE_UNIT_ATOMIC_INVENTORY


def scan_large_unit_candidates(raw_text: str) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    candidates: list[SurfaceCandidate] = []
    preserved_spans: set[tuple[int, int]] = set()
    index = 0
    while index < len(raw_text):
        if not (
            raw_text[index] in _LARGE_UNIT_SIGNS
            or _is_ascii_digit(raw_text[index])
            or raw_text[index] in _SMALL_UNITS
        ):
            index += 1
            continue

        parsed = _parse_large_unit_at(raw_text, index)
        if parsed is not None:
            if not _valid_boundaries(
                raw_text, parsed.core_span, raw_text[parsed.suffix_span.start]
            ):
                if (
                    parsed.core_span.end < len(raw_text)
                    and raw_text[parsed.core_span.end]
                    in _UNSAFE_FOLLOWING_DELIMITERS
                ):
                    span = parsed.core_span
                    candidates.append(
                        SurfaceCandidate(
                            core_span=span,
                            full_span=span,
                            owner="preserve",
                            surface_type="INVALID_LARGE_UNIT_DELIMITER_PRESERVE_SURFACE",
                            reason="large_unit_unapproved_delimiter_preserve",
                        )
                    )
                    index = span.end
                    continue
                preserve = _large_unit_like_preserve_candidate(raw_text, index)
                if preserve is not None:
                    key = (preserve.core_span.start, preserve.core_span.end)
                    if key not in preserved_spans:
                        preserved_spans.add(key)
                        candidates.append(preserve)
                        index = preserve.core_span.end
                        continue
                index += 1
                continue
            tail = raw_text[parsed.core_span.end :]
            unit_char = raw_text[parsed.suffix_span.start]
            if _has_disallowed_structured_decimal_tail(parsed, tail):
                preserve = _large_unit_like_preserve_candidate(raw_text, index)
                if preserve is not None:
                    key = (preserve.core_span.start, preserve.core_span.end)
                    if key not in preserved_spans:
                        preserved_spans.add(key)
                        candidates.append(preserve)
                        index = preserve.core_span.end
                        continue
                index += 1
                continue
            if _is_registered_counter_collision(unit_char, tail):
                index += 1
                continue
            if _is_disallowed_ascii_tail(tail) or tail.startswith(
                _AMBIGUOUS_SUFFIX_PREFIXES
            ):
                preserve = _large_unit_like_preserve_candidate(raw_text, index)
                if preserve is not None:
                    key = (preserve.core_span.start, preserve.core_span.end)
                    if key not in preserved_spans:
                        preserved_spans.add(key)
                        candidates.append(preserve)
                        index = preserve.core_span.end
                        continue
                index += 1
                continue
            candidates.append(_surface_candidate(parsed, tail))
            index = parsed.core_span.end
            continue

        preserve = _large_unit_like_preserve_candidate(raw_text, index)
        if preserve is not None:
            key = (preserve.core_span.start, preserve.core_span.end)
            if key not in preserved_spans:
                preserved_spans.add(key)
                candidates.append(preserve)
                index = preserve.core_span.end
                continue
        index += 1
    return candidates


def large_unit_render_pieces(
    raw_text: str, candidate: SurfaceCandidate
) -> list[RenderPiece] | None:
    if candidate.owner != "large_unit_atomic":
        return None
    render_parts = candidate.metadata.get("render_parts")
    if isinstance(render_parts, tuple) and render_parts:
        pieces: list[RenderPiece] = []
        for part in render_parts:
            if (
                not isinstance(part, tuple)
                or len(part) != 3
                or not isinstance(part[0], SourceSpan)
                or not isinstance(part[1], str)
                or not isinstance(part[2], str)
            ):
                return None
            pieces.append(
                RenderPiece(
                    text=part[1],
                    provenance=part[2],
                    source_span=part[0],
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            )
        return pieces
    reading = candidate.metadata.get("reading")
    numeric_span = candidate.metadata.get("numeric_span")
    suffix_span = candidate.metadata.get("suffix_span")
    insert_tail_space = candidate.metadata.get("insert_tail_space")
    reading_includes_suffix = candidate.metadata.get("reading_includes_suffix")
    if (
        not isinstance(reading, str)
        or not isinstance(numeric_span, SourceSpan)
        or not isinstance(suffix_span, SourceSpan)
        or not isinstance(insert_tail_space, bool)
    ):
        return None
    if reading_includes_suffix is True:
        suffix = raw_text[suffix_span.start : suffix_span.end]
        if suffix and suffix_span.end == candidate.core_span.end and reading.endswith(suffix):
            pieces = [
                RenderPiece(
                    text=reading[: -len(suffix)],
                    provenance="GENERATED_READING",
                    source_span=SourceSpan(candidate.core_span.start, suffix_span.start),
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                ),
                RenderPiece(
                    text=suffix,
                    provenance="ORIGINAL_KOREAN",
                    source_span=suffix_span,
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                ),
            ]
        else:
            pieces = [
                RenderPiece(
                    text=reading,
                    provenance="GENERATED_READING",
                    source_span=candidate.core_span,
                    owner=candidate.owner,
                    metadata={"surface_type": candidate.surface_type},
                )
            ]
    else:
        suffix = raw_text[suffix_span.start : suffix_span.end]
        pieces = [
            RenderPiece(
                text=reading,
                provenance="GENERATED_READING",
                source_span=numeric_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
            RenderPiece(
                text=suffix,
                provenance="ORIGINAL_KOREAN",
                source_span=suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            ),
        ]
    if insert_tail_space:
        pieces.append(
            RenderPiece(
                text=" ",
                provenance="GENERATED_READING",
                source_span=suffix_span,
                owner=candidate.owner,
                metadata={"surface_type": candidate.surface_type},
            )
        )
    return pieces


def _surface_candidate(parsed: _LargeUnitParse, tail: str) -> SurfaceCandidate:
    insert_tail_space = _needs_hangul_tail_spacing(tail)
    reading = parsed.reading
    if parsed.has_decimal and not parsed.reading_includes_suffix:
        reading = f"{reading}{SPOKEN_NUMERIC_BOUNDARY}"
    return SurfaceCandidate(
        core_span=parsed.core_span,
        full_span=parsed.core_span,
        owner="large_unit_atomic",
        surface_type="LARGE_UNIT_ATOMIC_SURFACE",
        suffix_spans=[parsed.suffix_span],
        reason=parsed.reason,
        metadata={
            "large_unit": parsed.suffix_span,
            "reading": reading,
            "reading_includes_suffix": parsed.reading_includes_suffix,
            "numeric_span": parsed.numeric_span,
            "suffix_span": parsed.suffix_span,
            "insert_tail_space": insert_tail_space,
            "render_parts": parsed.render_parts,
            **(
                {
                    "sign_profile": parsed.sign_profile,
                    "numeric_form": parsed.numeric_form,
                    "sign_surface": parsed.sign_surface,
                }
                if parsed.sign_profile is not None
                else {}
            ),
        },
    )


def _parse_large_unit_at(raw_text: str, start: int) -> _LargeUnitParse | None:
    return (
        _parse_structured_integer_large_unit_at(raw_text, start)
        or _parse_mixed_large_unit_at(raw_text, start)
        or _parse_numeric_large_unit_at(raw_text, start)
    )


@dataclass(frozen=True)
class _SmallGroupParse:
    end: int
    reading: str
    value: int
    final_bare_value: int | None
    saw_small_unit: bool
    saw_thousand: bool
    saw_lower_after_thousand: bool


@dataclass(frozen=True)
class MixedIntegerCoreParse:
    end: int
    reading: str
    value: int


@dataclass(frozen=True)
class LargeUnitQuantityCoreParse:
    end: int
    reading: str
    has_decimal: bool
    has_sign: bool
    integer_value: int | None
    numeric_reading: str
    numeric_span: SourceSpan
    suffix_span: SourceSpan
    reading_includes_suffix: bool


def parse_large_unit_integer_core_at(
    raw_text: str, start: int
) -> MixedIntegerCoreParse | None:
    """Parse a complete unsigned integer core containing a Korean large unit."""
    parsed = parse_large_unit_quantity_core_at(raw_text, start, allow_sign=False)
    if (
        parsed is None
        or parsed.has_decimal
        or parsed.has_sign
        or parsed.integer_value is None
        or parsed.integer_value < 0
    ):
        return None
    return MixedIntegerCoreParse(
        end=parsed.end,
        reading=parsed.reading,
        value=parsed.integer_value,
    )


def parse_large_unit_quantity_core_at(
    raw_text: str, start: int, *, allow_sign: bool = True
) -> LargeUnitQuantityCoreParse | None:
    """Parse an unsigned or signed large-unit core, including decimal forms."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(start, int):
        raise TypeError("start must be int")
    if start < 0 or start >= len(raw_text):
        return None
    if raw_text[start] in _LARGE_UNIT_SIGNS and not allow_sign:
        return None

    parsed = _parse_large_unit_at(raw_text, start)
    if parsed is None:
        return None
    has_sign = bool(parsed.sign_surface)
    if has_sign and not allow_sign:
        return None
    suffix = raw_text[parsed.suffix_span.start : parsed.suffix_span.end]
    numeric_reading = parsed.reading.rstrip()
    if parsed.reading_includes_suffix:
        reading = parsed.reading
    elif parsed.has_decimal:
        reading = f"{numeric_reading}{SPOKEN_NUMERIC_BOUNDARY}{suffix}"
    else:
        reading = f"{numeric_reading}{suffix}"
    return LargeUnitQuantityCoreParse(
        end=parsed.core_span.end,
        reading=reading,
        has_decimal=parsed.has_decimal,
        has_sign=has_sign,
        integer_value=parsed.integer_value,
        numeric_reading=numeric_reading,
        numeric_span=parsed.numeric_span,
        suffix_span=parsed.suffix_span,
        reading_includes_suffix=parsed.reading_includes_suffix,
    )


def parse_mixed_integer_core_at(
    raw_text: str, start: int
) -> MixedIntegerCoreParse | None:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    group = _parse_small_group(raw_text, start)
    if group is None or not group.saw_small_unit:
        return None
    return MixedIntegerCoreParse(
        end=group.end,
        reading=group.reading,
        value=group.value,
    )


def _parse_structured_integer_large_unit_at(
    raw_text: str, start: int
) -> _LargeUnitParse | None:
    if start >= len(raw_text):
        return None
    if raw_text[start] in _LARGE_UNIT_SIGNS:
        return None
    if not (_is_ascii_digit(raw_text[start]) or raw_text[start] in _SMALL_UNITS):
        return None

    index = start
    previous_large_order = len(_LARGE_UNIT_ORDER) + 1
    readings: list[str] = []
    render_parts: list[tuple[SourceSpan, str, str]] = []
    large_group_saw_small_units: list[bool] = []
    saw_large_unit = False
    last_large_unit_span: SourceSpan | None = None
    integer_value = 0

    while index < len(raw_text):
        group = _parse_small_group(raw_text, index)
        if group is None:
            break
        next_index = group.end
        if next_index < len(raw_text) and raw_text[next_index] == ".":
            if not saw_large_unit or last_large_unit_span is None:
                return None
            fraction_start = next_index + 1
            fraction_end = _consume_digits(raw_text, fraction_start)
            if fraction_end == fraction_start:
                return None
            if fraction_end < len(raw_text):
                next_char = raw_text[fraction_end]
                if (
                    next_char in _SMALL_UNITS
                    or is_large_unit(next_char)
                    or (
                        next_char == "."
                        and fraction_end + 1 < len(raw_text)
                        and _is_ascii_digit(raw_text[fraction_end + 1])
                    )
                ):
                    return None
            decimal_reading = join_decimal_prosody(
                group.reading, raw_text[fraction_start:fraction_end]
            )
            readings.append(decimal_reading)
            render_parts.extend(
                _structured_group_render_parts(
                    raw_text, index, next_index, decimal_end=fraction_end
                )
            )
            return _LargeUnitParse(
                core_span=SourceSpan(start, fraction_end),
                numeric_span=SourceSpan(start, fraction_end),
                suffix_span=last_large_unit_span,
                reading="".join(readings),
                has_decimal=True,
                reason="large_unit_structured_decimal_surface",
                reading_includes_suffix=True,
                render_parts=tuple(render_parts),
            )

        if next_index < len(raw_text) and is_large_unit(raw_text[next_index]):
            large_unit = raw_text[next_index]
            large_order = _LARGE_UNIT_ORDER[large_unit]
            if large_order >= previous_large_order:
                return None
            if _is_sparse_thousand_group_before_large(group):
                return None
            readings.append(f"{group.reading}{large_unit}")
            render_parts.extend(
                _structured_group_render_parts(raw_text, index, next_index)
            )
            render_parts.append(
                (
                    SourceSpan(next_index, next_index + 1),
                    large_unit,
                    "ORIGINAL_KOREAN",
                )
            )
            large_group_saw_small_units.append(group.saw_small_unit)
            integer_value += group.value * _LARGE_UNIT_VALUES[large_unit]
            saw_large_unit = True
            last_large_unit_span = SourceSpan(next_index, next_index + 1)
            previous_large_order = large_order
            index = next_index + 1
            continue

        if saw_large_unit:
            readings.append(group.reading)
            integer_value += group.value
            index = next_index
        break

    if not saw_large_unit or last_large_unit_span is None or index == start:
        return None
    if len(readings) == 1 and large_group_saw_small_units == [False]:
        return None
    return _LargeUnitParse(
        core_span=SourceSpan(start, index),
        numeric_span=SourceSpan(start, index),
        suffix_span=last_large_unit_span,
        reading="".join(readings),
        has_decimal=False,
        reason="large_unit_structured_integer_surface",
        reading_includes_suffix=True,
        integer_value=integer_value,
    )


def _parse_small_group(raw_text: str, start: int) -> _SmallGroupParse | None:
    index = start
    previous_small_order = 4
    parts: list[str] = []
    total = 0
    final_bare_value: int | None = None
    saw_small_unit = False
    saw_thousand = False
    saw_lower_after_thousand = False

    while index < len(raw_text):
        char = raw_text[index]
        if char in _SMALL_UNITS:
            order = _SMALL_UNIT_ORDER[char]
            if order >= previous_small_order:
                return None
            parts.append(char)
            total += _SMALL_UNITS[char]
            saw_small_unit = True
            saw_thousand = saw_thousand or order == 3
            saw_lower_after_thousand = saw_lower_after_thousand or (
                saw_thousand and order < 3
            )
            previous_small_order = order
            index += 1
            continue

        number_end = _consume_comma_integer(raw_text, index)
        if number_end == index:
            # A comma immediately after an otherwise valid digit block can be
            # sentence punctuation rather than an incomplete thousands group.
            # Boundary validation decides which case applies after the complete
            # mixed core has been parsed.
            number_end = _consume_digits(raw_text, index)
        if number_end == index:
            break
        number_text = raw_text[index:number_end]
        if len(number_text) > 1 and number_text.startswith("0"):
            return None
        number_reading = parse_signed_numeric(number_text)
        if number_reading is None:
            return None

        if number_end < len(raw_text) and raw_text[number_end] in _SMALL_UNITS:
            unit = raw_text[number_end]
            order = _SMALL_UNIT_ORDER[unit]
            if order >= previous_small_order:
                return None
            parts.append(f"{number_reading}{unit}")
            total += int(number_text.replace(",", "")) * _SMALL_UNITS[unit]
            saw_small_unit = True
            saw_thousand = saw_thousand or order == 3
            saw_lower_after_thousand = saw_lower_after_thousand or (
                saw_thousand and order < 3
            )
            previous_small_order = order
            index = number_end + 1
            continue

        parts.append(number_reading)
        final_bare_value = int(number_text.replace(",", ""))
        total += final_bare_value
        index = number_end
        break

    if index == start or not parts:
        return None
    if (
        final_bare_value is not None
        and saw_small_unit
        and not 0 < final_bare_value < (10 ** previous_small_order)
    ):
        return None
    return _SmallGroupParse(
        end=index,
        reading="".join(parts),
        value=total,
        final_bare_value=final_bare_value,
        saw_small_unit=saw_small_unit,
        saw_thousand=saw_thousand,
        saw_lower_after_thousand=saw_lower_after_thousand,
    )


def _structured_group_render_parts(
    raw_text: str, start: int, end: int, *, decimal_end: int | None = None
) -> tuple[tuple[SourceSpan, str, str], ...]:
    parts: list[tuple[SourceSpan, str, str]] = []
    index = start
    while index < end:
        if raw_text[index] in _SMALL_UNITS:
            parts.append(
                (
                    SourceSpan(index, index + 1),
                    raw_text[index],
                    "ORIGINAL_KOREAN",
                )
            )
            index += 1
            continue
        number_end = _consume_comma_integer(raw_text, index)
        if number_end == index:
            return ()
        reading_end = number_end
        number_text = raw_text[index:number_end]
        if decimal_end is not None and number_end == end:
            reading_end = decimal_end
            number_text = raw_text[index:decimal_end]
        reading = parse_signed_numeric(number_text)
        if reading is None:
            return ()
        parts.append(
            (SourceSpan(index, reading_end), reading, "GENERATED_READING")
        )
        index = reading_end
    return tuple(parts)


def _is_sparse_thousand_group_before_large(group: _SmallGroupParse) -> bool:
    return (
        group.saw_thousand
        and not group.saw_lower_after_thousand
        and group.final_bare_value is not None
        and 1 <= group.final_bare_value <= 9
    )


def _parse_numeric_large_unit_at(raw_text: str, start: int) -> _LargeUnitParse | None:
    index = start
    sign = ""
    if index < len(raw_text) and raw_text[index] in _LARGE_UNIT_SIGNS:
        sign = raw_text[index]
        index += 1

    numeric_start = index
    numeric_end = _consume_comma_integer(raw_text, numeric_start)
    if numeric_end == numeric_start:
        return None
    has_decimal = False
    if numeric_end < len(raw_text) and raw_text[numeric_end] == ".":
        fraction_start = numeric_end + 1
        fraction_end = _consume_digits(raw_text, fraction_start)
        if fraction_end == fraction_start:
            return None
        numeric_end = fraction_end
        has_decimal = True

    if numeric_end >= len(raw_text) or not is_large_unit(raw_text[numeric_end]):
        return None
    numeric_text = raw_text[numeric_start:numeric_end]
    policy = SIGNED_OWNER_POLICIES["large_unit_atomic"]
    core = parse_signed_numeric_core(
        sign + numeric_text,
        allow_plus=policy.accepts_plus,
        allow_minus=policy.accepts_minus,
        minus_aliases=policy.minus_aliases,
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
    return _LargeUnitParse(
        core_span=SourceSpan(start, numeric_end + 1),
        numeric_span=SourceSpan(start, numeric_end),
        suffix_span=SourceSpan(numeric_end, numeric_end + 1),
        reading=reading,
        has_decimal=has_decimal,
        reason="large_unit_numeric_surface",
        sign_profile=policy.sign_profile.value,
        numeric_form=core.numeric_form,
        sign_surface=core.sign_surface,
        integer_value=(
            int(numeric_text.replace(",", ""))
            * _LARGE_UNIT_VALUES[raw_text[numeric_end]]
            if not has_decimal and not sign
            else None
        ),
    )


def _parse_mixed_large_unit_at(raw_text: str, start: int) -> _LargeUnitParse | None:
    if start >= len(raw_text) or not _is_ascii_digit(raw_text[start]):
        return None
    index = start
    previous_order = 4
    total = 0
    parts: list[str] = []
    saw_small_unit = False
    saw_thousand = False
    saw_lower_after_thousand = False
    while index < len(raw_text):
        number_start = index
        integer_end = _consume_digits(raw_text, number_start)
        if integer_end == number_start:
            return None
        if integer_end < len(raw_text) and raw_text[integer_end] == ".":
            if not saw_small_unit:
                return None
            fraction_start = integer_end + 1
            fraction_end = _consume_digits(raw_text, fraction_start)
            if fraction_end == fraction_start:
                return None
            if fraction_end >= len(raw_text) or not is_large_unit(raw_text[fraction_end]):
                return None
            integer_value = int(raw_text[number_start:integer_end])
            if (
                saw_thousand
                and not saw_lower_after_thousand
                and 1 <= integer_value <= 9
            ):
                return None
            final_text = raw_text[number_start:fraction_end]
            final_reading = parse_signed_numeric(final_text)
            if final_reading is None:
                return None
            return _LargeUnitParse(
                core_span=SourceSpan(start, fraction_end + 1),
                numeric_span=SourceSpan(start, fraction_end),
                suffix_span=SourceSpan(fraction_end, fraction_end + 1),
                reading="".join(parts) + final_reading,
                has_decimal=True,
                reason="large_unit_mixed_arabic_hangul_decimal_surface",
            )

        number_text = raw_text[number_start:integer_end]
        if len(number_text) > 1 and number_text.startswith("0"):
            return None
        value = int(number_text)
        if integer_end < len(raw_text) and raw_text[integer_end] in _SMALL_UNITS:
            unit = raw_text[integer_end]
            order = _SMALL_UNIT_ORDER[unit]
            if order >= previous_order or value < 1 or value > 9:
                return None
            parts.append(f"{number_to_korean_under_10000(value)}{unit}")
            total += value * _SMALL_UNITS[unit]
            previous_order = order
            saw_small_unit = True
            saw_thousand = saw_thousand or order == 3
            saw_lower_after_thousand = saw_lower_after_thousand or (
                saw_thousand and order < 3
            )
            index = integer_end + 1
            continue

        if integer_end < len(raw_text) and is_large_unit(raw_text[integer_end]):
            if not saw_small_unit:
                return None
            if saw_thousand and not saw_lower_after_thousand and 1 <= value <= 9:
                return None
            total += value
            if total > 9999:
                return None
            parts.append(number_to_korean_under_10000(value) if value else "")
            return _LargeUnitParse(
                core_span=SourceSpan(start, integer_end + 1),
                numeric_span=SourceSpan(start, integer_end),
                suffix_span=SourceSpan(integer_end, integer_end + 1),
                reading="".join(parts),
                has_decimal=False,
                reason="large_unit_mixed_arabic_hangul_integer_surface",
                integer_value=total * _LARGE_UNIT_VALUES[raw_text[integer_end]],
            )

        if integer_end < len(raw_text) and is_large_unit(raw_text[integer_end]):
            return None
        return None


def _large_unit_like_preserve_candidate(
    raw_text: str, start: int
) -> SurfaceCandidate | None:
    token_start, token_end = _large_unit_like_token_bounds(raw_text, start)
    if token_end <= token_start:
        return None
    token = raw_text[token_start:token_end]
    if not any(_is_ascii_digit(char) for char in token):
        return None
    if not _has_plausible_large_unit_suffix(token) and not _has_invalid_small_unit_order_token(token):
        return None
    if _preceded_by_ordinal_je(raw_text, token_start):
        return None
    if _valid_large_unit_token(raw_text, token_start, token_end):
        return None
    span = SourceSpan(token_start, token_end)
    return SurfaceCandidate(
        core_span=span,
        full_span=span,
        owner="preserve",
        surface_type="INVALID_LARGE_UNIT_NUMERIC_PRESERVE_SURFACE",
        reason="invalid_large_unit_numeric_surface_preserve",
    )


def _valid_large_unit_token(raw_text: str, start: int, end: int) -> bool:
    parsed = _parse_large_unit_at(raw_text, start)
    if parsed is None:
        return False
    if not _valid_boundaries(
        raw_text, parsed.core_span, raw_text[parsed.suffix_span.start]
    ):
        return False
    tail = raw_text[parsed.core_span.end : end]
    if _has_disallowed_structured_decimal_tail(parsed, tail):
        return False
    if _is_registered_counter_collision(raw_text[parsed.suffix_span.start], tail):
        return True
    if _is_disallowed_ascii_tail(tail) or tail.startswith(_AMBIGUOUS_SUFFIX_PREFIXES):
        return False
    return True


def _large_unit_like_token_bounds(raw_text: str, start: int) -> tuple[int, int]:
    token_start = start
    while token_start > 0 and _is_large_unit_like_token_char(raw_text[token_start - 1]):
        token_start -= 1
    token_end = start
    while token_end < len(raw_text) and _is_large_unit_like_token_char(raw_text[token_end]):
        token_end += 1
    return token_start, token_end


def _is_large_unit_like_token_char(char: str) -> bool:
    if char in _TOKEN_CHARS:
        return True
    return "\uac00" <= char <= "\ud7a3"


def _has_plausible_large_unit_suffix(token: str) -> bool:
    for index, char in enumerate(token):
        if not is_large_unit(char):
            continue
        prefix = token[:index]
        if _is_plausible_large_unit_prefix(prefix):
            return True
        stripped = prefix.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        if stripped != prefix and _is_plausible_large_unit_prefix(stripped):
            return True
    return False


def _has_invalid_small_unit_order_token(token: str) -> bool:
    if not any(unit in token for unit in _SMALL_UNITS):
        return False
    compact = token.strip()
    token_prefix = compact.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    if token_prefix != compact:
        return False
    index = 0
    previous_order = 4
    saw_small_unit = False
    while index < len(compact):
        number_end = _consume_digits(compact, index)
        if number_end > index:
            index = number_end
            if index < len(compact) and compact[index] in _SMALL_UNITS:
                order = _SMALL_UNIT_ORDER[compact[index]]
                if order >= previous_order:
                    return True
                previous_order = order
                saw_small_unit = True
                index += 1
                continue
            continue
        if compact[index] in _SMALL_UNITS:
            order = _SMALL_UNIT_ORDER[compact[index]]
            if order >= previous_order:
                return True
            previous_order = order
            saw_small_unit = True
            index += 1
            continue
        return False
    return saw_small_unit and False


def _is_plausible_large_unit_prefix(prefix: str) -> bool:
    if not prefix or not any(_is_ascii_digit(char) for char in prefix):
        return False
    allowed = set("0123456789,.+-") | set(_SMALL_UNITS)
    return all(char in allowed for char in prefix)


def parse_large_unit_candidate(
    raw_text: str, candidate: SurfaceCandidate
) -> str | None:
    if candidate.owner != "large_unit_atomic":
        return None
    reading = candidate.metadata.get("reading")
    if isinstance(reading, str):
        if candidate.metadata.get("reading_includes_suffix") is True:
            return reading
        suffix_span = candidate.metadata.get("suffix_span")
        if isinstance(suffix_span, SourceSpan):
            return f"{reading}{raw_text[suffix_span.start:suffix_span.end]}"
        return reading
    raw_number = raw_text[candidate.core_span.start : candidate.core_span.end]
    if not _is_supported_large_unit_number(raw_number):
        return None
    return number_to_korean_under_10000(int(raw_number))


def is_unsafe_large_unit_tail(tail: str) -> bool:
    if not isinstance(tail, str):
        raise TypeError("tail must be str")
    if tail == "":
        return False
    if tail.startswith(_AMBIGUOUS_SUFFIX_PREFIXES):
        return True
    if _is_unsafe_ascii_tail(tail):
        return True
    first = tail[0]
    if first in {"-", "~", "∼"}:
        return True
    return False


def _is_unsafe_ascii_tail(tail: str) -> bool:
    if not tail:
        return False
    first = tail[0]
    return first.isascii() and first.isalnum()


def _is_disallowed_ascii_tail(tail: str) -> bool:
    if not tail:
        return False
    first = tail[0]
    if first.isascii() and first.isalpha():
        return False
    return first.isascii() and first.isalnum()


def _needs_hangul_tail_spacing(tail: str) -> bool:
    if not tail:
        return False
    first = tail[0]
    if not ("\uac00" <= first <= "\ud7a3"):
        return False
    if tail.startswith("여 ") or tail.startswith("여명"):
        return False
    return not tail.startswith(_ATTACHED_HANGUL_TAILS)


def _has_disallowed_structured_decimal_tail(
    parsed: _LargeUnitParse, tail: str
) -> bool:
    return (
        parsed.reason == "large_unit_structured_decimal_surface"
        and bool(tail)
        and tail[0].isascii()
        and tail[0].isalnum()
    )


def _is_registered_counter_collision(unit_char: str, tail: str) -> bool:
    return unit_char == "조" and tail.startswith("각")


def _is_supported_large_unit_number(number: str) -> bool:
    if not _is_ascii_digits(number):
        return False
    if len(number) > 1 and number.startswith("0"):
        return False
    return int(number) <= 9999


def _consume_digits(raw_text: str, start: int) -> int:
    index = start
    while index < len(raw_text) and _is_ascii_digit(raw_text[index]):
        index += 1
    return index


def _consume_comma_integer(raw_text: str, start: int) -> int:
    first_end = _consume_digits(raw_text, start)
    if first_end == start:
        return start
    if first_end < len(raw_text) and raw_text[first_end] == ",":
        first_len = first_end - start
        if first_len < 1 or first_len > 3:
            return start
        index = first_end
        while index < len(raw_text) and raw_text[index] == ",":
            group_start = index + 1
            group_end = _consume_digits(raw_text, group_start)
            if group_end - group_start != 3:
                return start
            index = group_end
        return index
    return first_end


def _is_ascii_digit(char: str) -> bool:
    return char.isascii() and char.isdigit()


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(char) for char in text)


def _preceded_by_ordinal_je(raw_text: str, number_start: int) -> bool:
    if (
        number_start > 1
        and raw_text[number_start - 1] == " "
        and raw_text[number_start - 2] == "제"
    ):
        return number_start == 2 or raw_text[number_start - 3].isspace()
    return False


def _valid_boundaries(raw_text: str, core_span: SourceSpan, unit_char: str) -> bool:
    prev_char = raw_text[core_span.start - 1] if core_span.start > 0 else None
    next_char = raw_text[core_span.end] if core_span.end < len(raw_text) else None

    if prev_char is not None:
        if prev_char.isascii() and prev_char.isalnum():
            return False
        if "\uac00" <= prev_char <= "\ud7a3":
            return False
        if prev_char in _PREV_BLOCKERS:
            return False
        if prev_char.isspace() and _preceded_by_ordinal_je(raw_text, core_span.start):
            return False
    if next_char is None:
        return True
    if next_char.isascii() and next_char.isalnum():
        return next_char.isalpha()
    if next_char in _SAFE_RIGHT_PUNCTUATION:
        return True
    if next_char in _NEXT_BLOCKERS:
        return False
    if next_char in _UNSAFE_FOLLOWING_DELIMITERS:
        return False
    if next_char == unit_char:
        return False
    return True


__all__ = [
    "LARGE_UNIT_ATOMIC_INVENTORY",
    "MixedIntegerCoreParse",
    "LargeUnitQuantityCoreParse",
    "is_large_unit",
    "is_unsafe_large_unit_tail",
    "large_unit_render_pieces",
    "parse_large_unit_candidate",
    "parse_large_unit_integer_core_at",
    "parse_large_unit_quantity_core_at",
    "parse_mixed_integer_core_at",
    "scan_large_unit_candidates",
]
