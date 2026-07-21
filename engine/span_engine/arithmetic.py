from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from engine.span_engine.brackets import BracketRange
from engine.span_engine.counter import is_emergency_ambiguous_number
from engine.span_engine.fraction import FractionOperandParse, parse_fraction_operand_at
from engine.span_engine.hyphen import is_hyphen_digit_candidate
from engine.span_engine.models import RenderPiece, SourceSpan, Surface, SurfaceCandidate
from engine.span_engine.particle import final_hangul_syllable, has_jongseong
from engine.span_engine.phone import is_exact_4_4_phone, is_international_phone
from engine.span_engine.sign_aliases import MINUS_SIGN_ALIASES
from engine.span_engine.signed_numeric import (
    SignProfile,
    SignedNumericCore,
    parse_signed_numeric_core,
    render_signed_numeric,
)


class ExpectedToken(Enum):
    OPERAND = "operand"
    OPERATOR_OR_EQUALS_OR_END = "operator_or_equals_or_end"


@dataclass(frozen=True)
class ArithmeticOperand:
    source_span: SourceSpan
    kind: str
    reading: str
    parsed_surface: SignedNumericCore | FractionOperandParse


@dataclass(frozen=True)
class ArithmeticOperator:
    source_span: SourceSpan
    kind: str
    source_surface: str


@dataclass(frozen=True)
class ArithmeticExpressionParse:
    source_span: SourceSpan
    tokens: tuple[ArithmeticOperand | ArithmeticOperator, ...]
    operand_kinds: tuple[str, ...]
    operator_kinds: tuple[str, ...]
    has_equality: bool


ARITHMETIC_OPERATOR_POLICIES: dict[str, tuple[str, str]] = {
    "+": ("ADD", "더하기"),
    "-": ("SUBTRACT", "빼기"),
    "×": ("MULTIPLY", "곱하기"),
    "x": ("MULTIPLY", "곱하기"),
    "÷": ("DIVIDE", "나누기"),
}

_UNSIGNED_NUMERIC_PREFIX_RE = re.compile(
    r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
)
_OPERATORS = frozenset(ARITHMETIC_OPERATOR_POLICIES)
_UNSUPPORTED_EXPRESSION_MARKERS = frozenset({"X", "*", "^", "(", ")"})
_ARITHMETIC_MARKERS = _OPERATORS | _UNSUPPORTED_EXPRESSION_MARKERS | frozenset({"=", "/"})
_BOUNDARY_BLOCKERS = _ARITHMETIC_MARKERS | frozenset({".", "/", "_", "%", "℃", "℉", "°", "º"})
_ALLOWED_KOREAN_TAILS = (
    "이고",
    "이며",
    "이다",
    "였다",
    "입니다",
    "였고",
    "였지만",
)
_PARENTHESIZED_ARITHMETIC_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"\([^()\r\n]+\)"
    r"(?:[+\-×x÷][+\-−－]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)?"
    r"(?![A-Za-z0-9_])"
)
_FUNCTION_CALL_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"[A-Za-z_][A-Za-z0-9_]*"
    r"\([0-9,+\-−－. /×x÷=*^]+\)"
    r"(?![A-Za-z0-9_])"
)


def parse_basic_arithmetic_expression_at(
    raw_text: str,
    start: int,
) -> ArithmeticExpressionParse | None:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if not isinstance(start, int):
        raise TypeError("start must be int")
    if start < 0 or start >= len(raw_text):
        return None
    if not _valid_left_boundary(raw_text, start):
        return None

    cursor = start
    state = ExpectedToken.OPERAND
    tokens: list[ArithmeticOperand | ArithmeticOperator] = []
    operand_kinds: list[str] = []
    operator_kinds: list[str] = []
    binary_operator_count = 0
    has_equality = False
    last_binary_surface: str | None = None
    last_operator_had_post_space = False

    while True:
        if state is ExpectedToken.OPERAND:
            operand = _parse_operand_at(raw_text, cursor)
            if operand is None:
                return None
            if (
                last_binary_surface in {"+", "-"}
                and not last_operator_had_post_space
                and raw_text[cursor] in ({"+"} | MINUS_SIGN_ALIASES)
            ):
                return None
            tokens.append(operand)
            operand_kinds.append(operand.kind)
            cursor = operand.source_span.end
            state = ExpectedToken.OPERATOR_OR_EQUALS_OR_END
            continue

        operator_start, operator_surface, post_space, spacing_invalid = (
            _scan_next_operator(raw_text, cursor)
        )
        if spacing_invalid:
            return None
        if operator_surface is None:
            break

        if operator_surface == "=":
            if has_equality:
                return None
            has_equality = True
            operator_kind = "EQUALS"
        else:
            operator_kind = ARITHMETIC_OPERATOR_POLICIES[operator_surface][0]
            binary_operator_count += 1

        operator_span = SourceSpan(operator_start, operator_start + 1)
        tokens.append(
            ArithmeticOperator(
                source_span=operator_span,
                kind=operator_kind,
                source_surface=operator_surface,
            )
        )
        operator_kinds.append(operator_kind)
        cursor = operator_start + 1 + post_space
        last_binary_surface = operator_surface if operator_surface != "=" else None
        last_operator_had_post_space = post_space == 1
        state = ExpectedToken.OPERAND

    if state is ExpectedToken.OPERAND or binary_operator_count < 1:
        return None
    if not _valid_right_boundary(raw_text, cursor):
        return None

    raw = raw_text[start:cursor]
    if not _binary_minus_policy_allows(raw_text, tokens, has_equality):
        return None
    if _is_existing_phone_surface(raw) or _defer_to_existing_hyphen_owner(raw, tokens):
        return None
    return ArithmeticExpressionParse(
        source_span=SourceSpan(start, cursor),
        tokens=tuple(tokens),
        operand_kinds=tuple(operand_kinds),
        operator_kinds=tuple(operator_kinds),
        has_equality=has_equality,
    )


def is_strict_basic_arithmetic_expression(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text or text != text.strip():
        return False
    parsed = parse_basic_arithmetic_expression_at(text, 0)
    return parsed is not None and parsed.source_span.end == len(text)


def scan_basic_arithmetic_expression_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None = None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _could_start_operand(raw_text[index]):
            index += 1
            continue
        parsed = parse_basic_arithmetic_expression_at(raw_text, index)
        if parsed is None:
            index += 1
            continue
        if _span_overlaps_excluded_range(parsed.source_span, excluded_ranges):
            index = parsed.source_span.end
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=parsed.source_span,
                full_span=parsed.source_span,
                owner="basic_arithmetic_expression",
                surface_type="BASIC_ARITHMETIC_EXPRESSION_SURFACE",
                reason="basic_arithmetic_expression_full_consume_gate",
                metadata={
                    "operand_kinds": parsed.operand_kinds,
                    "operator_kinds": parsed.operator_kinds,
                    "has_equality": parsed.has_equality,
                },
            )
        )
        index = parsed.source_span.end
    return candidates


def is_invalid_basic_arithmetic_expression_text(text: str) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text or text != text.strip():
        return False
    return (
        _consume_arithmetic_like_token(text, 0) == len(text)
        and _has_invalid_arithmetic_intent(text)
    )


def unsupported_parenthesized_arithmetic_spans(raw_text: str) -> list[SourceSpan]:
    """Return narrow parenthesized/function tokens that arithmetic must preserve."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")

    spans: list[SourceSpan] = []
    for match in _PARENTHESIZED_ARITHMETIC_TOKEN_RE.finditer(raw_text):
        raw = match.group(0)
        inner_end = raw.find(")")
        inner = raw[1:inner_end]
        has_inner_expression = is_strict_basic_arithmetic_expression(inner)
        has_outer_operator = inner_end + 1 < len(raw)
        if not has_inner_expression and not has_outer_operator:
            continue
        spans.append(SourceSpan(match.start(), match.end()))

    for match in _FUNCTION_CALL_TOKEN_RE.finditer(raw_text):
        span = SourceSpan(match.start(), match.end())
        if any(span.start < current.end and current.start < span.end for current in spans):
            continue
        spans.append(span)
    return sorted(spans, key=lambda span: span.start)


def scan_invalid_basic_arithmetic_preserve_candidates(
    raw_text: str,
    excluded_ranges: list[BracketRange] | None = None,
) -> list[SurfaceCandidate]:
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be str")
    if excluded_ranges is None:
        excluded_ranges = []
    candidates: list[SurfaceCandidate] = []
    index = 0
    while index < len(raw_text):
        if not _could_start_arithmetic_like_token(raw_text[index]):
            index += 1
            continue
        end = _consume_arithmetic_like_token(raw_text, index)
        if end <= index:
            index += 1
            continue
        span = SourceSpan(index, end)
        raw = raw_text[index:end]
        if not _has_invalid_arithmetic_intent(raw):
            index = end
            continue
        if _span_overlaps_excluded_range(span, excluded_ranges):
            index = end
            continue
        candidates.append(
            SurfaceCandidate(
                core_span=span,
                full_span=span,
                owner="preserve",
                surface_type="INVALID_BASIC_ARITHMETIC_EXPRESSION_PRESERVE_SURFACE",
                reason="invalid_basic_arithmetic_expression_preserve",
                metadata={
                    "preserve_reason": "arithmetic_full_consume_or_operand_validation_failed",
                },
            )
        )
        index = end
    return candidates


def parse_basic_arithmetic_candidate(
    raw_text: str,
    candidate: SurfaceCandidate,
) -> Surface | None:
    if candidate.owner != "basic_arithmetic_expression":
        return None
    parsed = parse_basic_arithmetic_expression_at(raw_text, candidate.core_span.start)
    if parsed is None or parsed.source_span != candidate.core_span:
        return None

    render_pieces: list[RenderPiece] = []
    previous_operand: ArithmeticOperand | None = None
    for token in parsed.tokens:
        if isinstance(token, ArithmeticOperand):
            render_pieces.append(
                RenderPiece(
                    text=token.reading,
                    provenance="GENERATED_READING",
                    source_span=token.source_span,
                    owner=candidate.owner,
                    metadata={
                        "surface_type": candidate.surface_type,
                        "arithmetic_token_kind": token.kind,
                    },
                )
            )
            previous_operand = token
            continue

        if token.kind == "EQUALS":
            if previous_operand is None:
                return None
            operator_reading = _equals_reading(previous_operand.reading) + " "
        else:
            operator_reading = (
                " "
                + ARITHMETIC_OPERATOR_POLICIES[token.source_surface][1]
                + " "
            )
        render_pieces.append(
            RenderPiece(
                text=operator_reading,
                provenance="GENERATED_READING",
                source_span=token.source_span,
                owner=candidate.owner,
                metadata={
                    "surface_type": candidate.surface_type,
                    "arithmetic_token_kind": token.kind,
                    "source_surface": token.source_surface,
                },
            )
        )

    reading = "".join(piece.text for piece in render_pieces)
    return Surface(
        surface_type=candidate.surface_type or "BASIC_ARITHMETIC_EXPRESSION_SURFACE",
        owner=candidate.owner,
        raw=raw_text[candidate.core_span.start : candidate.core_span.end],
        span=candidate.core_span,
        reading=reading,
        render_pieces=render_pieces,
        metadata={
            "reason": candidate.reason,
            "operand_kinds": parsed.operand_kinds,
            "operator_kinds": parsed.operator_kinds,
            "has_equality": parsed.has_equality,
        },
    )


def _parse_operand_at(raw_text: str, start: int) -> ArithmeticOperand | None:
    fraction = parse_fraction_operand_at(raw_text, start)
    if fraction is not None:
        return ArithmeticOperand(
            source_span=fraction.source_span,
            kind="FRACTION",
            reading=fraction.reading,
            parsed_surface=fraction,
        )

    sign_end = start
    if raw_text[start] == "+" or raw_text[start] in MINUS_SIGN_ALIASES:
        sign_end += 1
    match = _UNSIGNED_NUMERIC_PREFIX_RE.match(raw_text, sign_end)
    if match is None:
        return None
    end = match.end()
    raw = raw_text[start:end]
    core = parse_signed_numeric_core(raw)
    if core is None:
        return None
    reading = render_signed_numeric(core, sign_profile=SignProfile.DEFAULT)
    if reading is None:
        return None
    kind = "SIGNED_NUMBER" if core.sign_kind is not None else "NUMBER"
    return ArithmeticOperand(
        source_span=SourceSpan(start, end),
        kind=kind,
        reading=reading,
        parsed_surface=core,
    )


def _scan_next_operator(
    raw_text: str,
    cursor: int,
) -> tuple[int, str | None, int, bool]:
    operator_start = cursor
    if operator_start < len(raw_text) and raw_text[operator_start] == " ":
        operator_start += 1
        if operator_start < len(raw_text) and raw_text[operator_start] == " ":
            next_non_space = operator_start
            while next_non_space < len(raw_text) and raw_text[next_non_space] == " ":
                next_non_space += 1
            if next_non_space < len(raw_text) and raw_text[next_non_space] in (_OPERATORS | {"="}):
                return cursor, None, 0, True
            return cursor, None, 0, False
    elif operator_start < len(raw_text) and raw_text[operator_start].isspace():
        next_non_space = operator_start
        while next_non_space < len(raw_text) and raw_text[next_non_space].isspace():
            next_non_space += 1
        if next_non_space < len(raw_text) and raw_text[next_non_space] in (_OPERATORS | {"="}):
            return cursor, None, 0, True
        return cursor, None, 0, False

    if operator_start >= len(raw_text):
        return cursor, None, 0, False
    surface = raw_text[operator_start]
    if surface not in (_OPERATORS | {"="}):
        return cursor, None, 0, False

    after_operator = operator_start + 1
    post_space = 0
    if after_operator < len(raw_text) and raw_text[after_operator] == " ":
        post_space = 1
        if (
            after_operator + 1 < len(raw_text)
            and raw_text[after_operator + 1] == " "
        ):
            return operator_start, surface, 0, True
    elif after_operator < len(raw_text) and raw_text[after_operator].isspace():
        return operator_start, surface, 0, True
    return operator_start, surface, post_space, False


def _equals_reading(left_operand_reading: str) -> str:
    tail = final_hangul_syllable(left_operand_reading)
    if tail is None:
        raise ValueError("arithmetic operand reading must end in Hangul")
    return "은" if has_jongseong(tail) else "는"


def _valid_left_boundary(raw_text: str, start: int) -> bool:
    if start == 0:
        return True
    previous_index = start - 1
    previous = raw_text[previous_index]
    if previous.isspace():
        while previous_index >= 0 and raw_text[previous_index].isspace():
            previous_index -= 1
        if (
            previous_index >= 0
            and raw_text[previous_index] in (_ARITHMETIC_MARKERS | {"."})
        ):
            return False
        return True
    if previous.isascii() and previous.isalnum():
        return False
    if "\uac00" <= previous <= "\ud7a3":
        return False
    return previous not in ({"_", ".", ",", "/"} | _ARITHMETIC_MARKERS)


def _valid_right_boundary(raw_text: str, end: int) -> bool:
    if end >= len(raw_text):
        return True
    next_char = raw_text[end]
    if next_char.isspace():
        next_non_space = end
        while next_non_space < len(raw_text) and raw_text[next_non_space].isspace():
            next_non_space += 1
        if next_non_space < len(raw_text) and raw_text.startswith("무", next_non_space):
            return False
        return not (
            next_non_space < len(raw_text)
            and raw_text[next_non_space] in (_ARITHMETIC_MARKERS | {"."})
        )
    if next_char == ",":
        return end + 1 >= len(raw_text) or not raw_text[end + 1].isdigit()
    if next_char.isascii() and next_char.isalnum():
        return False
    if next_char in _BOUNDARY_BLOCKERS:
        return False
    if "\uac00" <= next_char <= "\ud7a3":
        tail = raw_text[end:]
        return any(tail.startswith(value) for value in _ALLOWED_KOREAN_TAILS)
    return True


def _could_start_operand(char: str) -> bool:
    return (char.isascii() and char.isdigit()) or char == "+" or char in MINUS_SIGN_ALIASES


def _could_start_arithmetic_like_token(char: str) -> bool:
    return (
        _could_start_operand(char)
        or char in {"x", "X", "(", "."}
    )


def _consume_arithmetic_like_token(raw_text: str, start: int) -> int:
    cursor = start
    while cursor < len(raw_text):
        char = raw_text[cursor]
        if char in "\r\n\t ":
            if raw_text[start].isascii() and raw_text[start].isalpha():
                break
            next_non_space = cursor
            while next_non_space < len(raw_text) and raw_text[next_non_space] in "\r\n\t ":
                next_non_space += 1
            previous = raw_text[cursor - 1] if cursor > start else ""
            next_char = raw_text[next_non_space] if next_non_space < len(raw_text) else ""
            if previous in _ARITHMETIC_MARKERS or next_char in _ARITHMETIC_MARKERS:
                cursor = next_non_space
                continue
            break
        if char == ",":
            previous = raw_text[cursor - 1] if cursor > start else ""
            next_char = raw_text[cursor + 1] if cursor + 1 < len(raw_text) else ""
            if previous.isdigit() and next_char.isdigit():
                cursor += 1
                continue
            break
        if "\uac00" <= char <= "\ud7a3":
            hangul_end = cursor
            while (
                hangul_end < len(raw_text)
                and "\uac00" <= raw_text[hangul_end] <= "\ud7a3"
            ):
                hangul_end += 1
            prefix = raw_text[start:cursor]
            if _is_existing_phone_surface(prefix) or is_hyphen_digit_candidate(prefix):
                break
            prefix_body = (
                prefix[1:]
                if prefix and (prefix[0] == "+" or prefix[0] in MINUS_SIGN_ALIASES)
                else prefix
            )
            next_char = raw_text[hangul_end] if hangul_end < len(raw_text) else ""
            if next_char in _ARITHMETIC_MARKERS or any(
                marker in prefix_body for marker in _ARITHMETIC_MARKERS
            ):
                cursor = hangul_end
                continue
            break
        if char.isalnum() or char in (
            _ARITHMETIC_MARKERS
            | frozenset({".", "_", "%", "$", "₩", "℃", "℉", "°", "º", "㎡"})
        ):
            cursor += 1
            continue
        break
    return cursor


def _has_invalid_arithmetic_intent(raw: str) -> bool:
    if not any(char.isascii() and char.isdigit() for char in raw):
        return False
    if _is_existing_phone_surface(raw) or is_hyphen_digit_candidate(raw):
        return False
    if is_strict_basic_arithmetic_expression(raw):
        return False
    if "^" in raw and any(char.isascii() and char.isalpha() for char in raw):
        return False
    if any(
        raw[index] in _ARITHMETIC_MARKERS
        and index + 1 < len(raw)
        and "\uac00" <= raw[index + 1] <= "\ud7a3"
        for index in range(len(raw))
    ):
        return False
    fraction = parse_fraction_operand_at(raw, 0)
    if fraction is not None and fraction.source_span.end == len(raw):
        return False
    if parse_signed_numeric_core(raw) is not None:
        return False

    body = raw[1:] if raw and (raw[0] == "+" or raw[0] in MINUS_SIGN_ALIASES) else raw
    leading_sign_count = 0
    while (
        leading_sign_count < len(raw)
        and (raw[leading_sign_count] == "+" or raw[leading_sign_count] in MINUS_SIGN_ALIASES)
    ):
        leading_sign_count += 1
    if leading_sign_count > 1:
        unsigned_tail = raw[leading_sign_count:]
        if parse_signed_numeric_core(unsigned_tail) is not None:
            return False
    markers = [
        char
        for index, char in enumerate(body)
        if char in _ARITHMETIC_MARKERS
        and (char != "x" or (index > 0 and body[index - 1].isdigit()))
    ]
    if not markers:
        return False
    if set(markers) == {"/"}:
        return False
    return True


def _binary_minus_policy_allows(
    raw_text: str,
    tokens: list[ArithmeticOperand | ArithmeticOperator],
    has_equality: bool,
) -> bool:
    qualifying_compact_context = has_equality or any(
        isinstance(token, ArithmeticOperator)
        and token.kind in {"ADD", "MULTIPLY", "DIVIDE"}
        for token in tokens
    )
    for index, token in enumerate(tokens):
        if not isinstance(token, ArithmeticOperator) or token.kind != "SUBTRACT":
            continue
        if index == 0 or index + 1 >= len(tokens):
            return False
        previous = tokens[index - 1]
        following = tokens[index + 1]
        if not isinstance(previous, ArithmeticOperand) or not isinstance(
            following, ArithmeticOperand
        ):
            return False
        before = raw_text[previous.source_span.end : token.source_span.start]
        after = raw_text[token.source_span.end : following.source_span.start]
        if before == " " and after == " ":
            continue
        if before == "" and after == "" and qualifying_compact_context:
            continue
        return False
    return True


def _defer_to_existing_hyphen_owner(
    raw: str,
    tokens: list[ArithmeticOperand | ArithmeticOperator],
) -> bool:
    operators = [token for token in tokens if isinstance(token, ArithmeticOperator)]
    operands = [token for token in tokens if isinstance(token, ArithmeticOperand)]
    if operators and all(token.kind == "SUBTRACT" for token in operators):
        numeric_operands = [
            token.parsed_surface
            for token in operands
            if isinstance(token.parsed_surface, SignedNumericCore)
        ]
        if len(numeric_operands) == len(operands):
            has_space = " " in raw
            if not has_space and raw.startswith(tuple(MINUS_SIGN_ALIASES)):
                return True
            if not has_space and any(core.has_decimal for core in numeric_operands):
                return True
            if len(operators) == 1 and not has_space:
                return any(len(core.integer_digits) > 1 for core in numeric_operands)
            if len(operators) >= 2:
                if len(numeric_operands[0].integer_digits) == 1:
                    return True
                if any(
                    core.has_decimal or len(core.integer_digits) > 1
                    for core in numeric_operands[1:]
                ):
                    return True

    compact_raw = raw.replace(" ", "")
    if not is_hyphen_digit_candidate(compact_raw):
        return False
    blocks = compact_raw.split("-")
    compact_digits = "".join(blocks)
    if is_emergency_ambiguous_number(compact_digits):
        return True
    if len(blocks) >= 3 and (len(blocks[0]) == 1 or len(blocks[0]) == 4):
        return True
    return any(len(block) > 1 for block in blocks[1:])


def _is_existing_phone_surface(raw: str) -> bool:
    if is_international_phone(raw):
        return True
    if not is_exact_4_4_phone(raw):
        return False
    left, right = raw.split("-", 1)
    return (
        left.isascii()
        and left.isdigit()
        and right.isascii()
        and right.isdigit()
    )


def _span_overlaps_excluded_range(
    span: SourceSpan,
    excluded_ranges: list[BracketRange],
) -> bool:
    return any(
        span.start < bracket_range.span.end and bracket_range.span.start < span.end
        for bracket_range in excluded_ranges
    )


__all__ = [
    "ARITHMETIC_OPERATOR_POLICIES",
    "ArithmeticExpressionParse",
    "ArithmeticOperand",
    "ArithmeticOperator",
    "ExpectedToken",
    "is_invalid_basic_arithmetic_expression_text",
    "is_strict_basic_arithmetic_expression",
    "parse_basic_arithmetic_candidate",
    "parse_basic_arithmetic_expression_at",
    "scan_basic_arithmetic_expression_candidates",
    "scan_invalid_basic_arithmetic_preserve_candidates",
    "unsupported_parenthesized_arithmetic_spans",
]
