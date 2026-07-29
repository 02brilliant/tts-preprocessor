from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.span_engine.numeric_reading import (
    normalize_integer_text,
    read_decimal_fraction_digits,
    read_integer_text,
    read_spaced_integer_text,
)
from engine.span_engine.sign_aliases import MINUS_SIGN_ALIASES, PLUS_SIGN


class SignKind(Enum):
    PLUS = "PLUS"
    MINUS = "MINUS"


class SignProfile(Enum):
    DEFAULT = "default"
    TEMPERATURE = "temperature"
    UNSIGNED_ONLY = "unsigned_only"
    OWNER_CUSTOM = "owner_custom"


@dataclass(frozen=True)
class NumericCore:
    raw: str
    integer_raw: str
    integer_digits: str
    fractional_digits: str | None
    had_comma: bool

    @property
    def has_decimal(self) -> bool:
        return self.fractional_digits is not None

    @property
    def numeric_form(self) -> str:
        if self.has_decimal:
            return "COMMA_DECIMAL" if self.had_comma else "DECIMAL"
        return "COMMA_INTEGER" if self.had_comma else "INTEGER"


@dataclass(frozen=True)
class SignedNumericCore:
    raw: str
    sign_kind: SignKind | None
    number: NumericCore
    sign_surface: str | None

    @property
    def integer_raw(self) -> str:
        return self.number.integer_raw

    @property
    def integer_digits(self) -> str:
        return self.number.integer_digits

    @property
    def fractional_digits(self) -> str | None:
        return self.number.fractional_digits

    @property
    def has_decimal(self) -> bool:
        return self.number.has_decimal

    @property
    def numeric_form(self) -> str:
        return self.number.numeric_form

    @property
    def is_negative(self) -> bool:
        return self.sign_kind is SignKind.MINUS

    @property
    def is_positive(self) -> bool:
        return self.sign_kind is SignKind.PLUS


@dataclass(frozen=True)
class SignedOwnerPolicy:
    accepts_plus: bool
    accepts_minus: bool
    minus_aliases: frozenset[str]
    sign_profile: SignProfile
    numeric_forms: frozenset[str]
    attachment_policy: str
    full_consume_required: bool = True


_STANDARD_NUMERIC_FORMS = frozenset(
    {"INTEGER", "COMMA_INTEGER", "DECIMAL", "COMMA_DECIMAL"}
)
_ASCII_MINUS_ONLY = frozenset({"-"})
_FRACTION_MINUS_ALIASES = frozenset({"-", "−", "－"})

DEFAULT_SIGNED_OWNER_POLICY = SignedOwnerPolicy(
    accepts_plus=True,
    accepts_minus=True,
    minus_aliases=MINUS_SIGN_ALIASES,
    sign_profile=SignProfile.DEFAULT,
    numeric_forms=_STANDARD_NUMERIC_FORMS,
    attachment_policy="standalone_numeric",
)

SIGNED_OWNER_POLICIES: dict[str, SignedOwnerPolicy] = {
    "signed_number": DEFAULT_SIGNED_OWNER_POLICY,
    "simple_unit": SignedOwnerPolicy(
        True,
        True,
        MINUS_SIGN_ALIASES,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS,
        "registered_unit_attached_or_one_ascii_space",
    ),
    "special_unit": SignedOwnerPolicy(
        True,
        True,
        MINUS_SIGN_ALIASES,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS,
        "registered_unit_attached_or_one_ascii_space",
    ),
    "currency": SignedOwnerPolicy(
        True,
        True,
        _ASCII_MINUS_ONLY,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS,
        "registered_currency_marker",
    ),
    "percent_point": SignedOwnerPolicy(
        True,
        True,
        MINUS_SIGN_ALIASES,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS | frozenset({"FRACTION"}),
        "registered_percent_point_marker",
    ),
    "large_unit_atomic": SignedOwnerPolicy(
        True,
        True,
        _ASCII_MINUS_ONLY,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS,
        "registered_large_unit_attached",
    ),
    "fraction": SignedOwnerPolicy(
        False,
        True,
        _FRACTION_MINUS_ALIASES,
        SignProfile.DEFAULT,
        frozenset({"FRACTION"}),
        "slash_fraction",
    ),
    "colon_semantic_pair": SignedOwnerPolicy(
        True,
        True,
        _ASCII_MINUS_ONLY,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS,
        "owner_operand",
    ),
    "range": SignedOwnerPolicy(
        True,
        True,
        _ASCII_MINUS_ONLY,
        SignProfile.DEFAULT,
        _STANDARD_NUMERIC_FORMS,
        "tilde_endpoint_only",
    ),
    "signed_temperature": SignedOwnerPolicy(
        True,
        True,
        MINUS_SIGN_ALIASES,
        SignProfile.TEMPERATURE,
        _STANDARD_NUMERIC_FORMS,
        "temperature_symbol_attached",
    ),
    "signed_degree": SignedOwnerPolicy(
        True,
        True,
        MINUS_SIGN_ALIASES,
        SignProfile.OWNER_CUSTOM,
        _STANDARD_NUMERIC_FORMS,
        "degree_symbol_attached",
    ),
    "compound_slash_unit": SignedOwnerPolicy(
        False,
        False,
        frozenset(),
        SignProfile.UNSIGNED_ONLY,
        _STANDARD_NUMERIC_FORMS,
        "compound_unit_existing_unsigned_only",
    ),
    "phone": SignedOwnerPolicy(
        True,
        False,
        frozenset(),
        SignProfile.OWNER_CUSTOM,
        frozenset({"DIGIT_SEQUENCE"}),
        "international_phone_plus_route",
    ),
    "counter_noun": SignedOwnerPolicy(
        False,
        False,
        frozenset(),
        SignProfile.UNSIGNED_ONLY,
        frozenset({"INTEGER", "COMMA_INTEGER"}),
        "existing_counter_policy",
    ),
    "ambiguous_numeric_dae_preserve": SignedOwnerPolicy(
        False,
        False,
        frozenset(),
        SignProfile.UNSIGNED_ONLY,
        frozenset(),
        "atomic_preserve",
    ),
}


def parse_signed_numeric_core(
    text: str,
    *,
    allow_plus: bool = True,
    allow_minus: bool = True,
    minus_aliases: frozenset[str] = MINUS_SIGN_ALIASES,
    require_sign: bool = False,
    numeric_forms: frozenset[str] = _STANDARD_NUMERIC_FORMS,
) -> SignedNumericCore | None:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    if not text or text != text.strip():
        return None

    sign: SignKind | None = None
    sign_surface: str | None = None
    unsigned = text
    if text.startswith(PLUS_SIGN):
        if not allow_plus:
            return None
        sign = SignKind.PLUS
        sign_surface = PLUS_SIGN
        unsigned = text[1:]
    elif text[0] in minus_aliases:
        if not allow_minus:
            return None
        sign = SignKind.MINUS
        sign_surface = text[0]
        unsigned = text[1:]
    elif require_sign:
        return None

    if not unsigned or unsigned.count(".") > 1:
        return None
    integer_raw = unsigned
    fractional_digits: str | None = None
    if "." in unsigned:
        integer_raw, fractional_digits = unsigned.split(".", 1)
        if (
            not fractional_digits
            or not fractional_digits.isascii()
            or not fractional_digits.isdigit()
        ):
            return None

    integer_digits = normalize_integer_text(integer_raw)
    if integer_digits is None:
        return None
    number = NumericCore(
        raw=unsigned,
        integer_raw=integer_raw,
        integer_digits=integer_digits,
        fractional_digits=fractional_digits,
        had_comma="," in integer_raw,
    )
    if number.numeric_form not in numeric_forms:
        return None
    try:
        if read_integer_text(integer_raw) is None:
            return None
    except ValueError:
        return None
    return SignedNumericCore(
        raw=text,
        sign_kind=sign,
        number=number,
        sign_surface=sign_surface,
    )


def render_sign(sign: SignKind | None, profile: SignProfile) -> str | None:
    if sign is None:
        return ""
    if profile is SignProfile.DEFAULT:
        return "플러스" if sign is SignKind.PLUS else "마이너스"
    if profile is SignProfile.TEMPERATURE:
        return "영상" if sign is SignKind.PLUS else "영하"
    if profile is SignProfile.UNSIGNED_ONLY:
        return None
    return None


def parse_sign_surface(
    sign_surface: str | None,
    *,
    minus_aliases: frozenset[str] = MINUS_SIGN_ALIASES,
) -> SignKind | None:
    if sign_surface is None or sign_surface == "":
        return None
    if sign_surface == PLUS_SIGN:
        return SignKind.PLUS
    if sign_surface in minus_aliases:
        return SignKind.MINUS
    return None


def apply_sign_profile(
    reading: str,
    sign: SignKind | None,
    *,
    sign_profile: SignProfile = SignProfile.DEFAULT,
) -> str | None:
    sign_reading = render_sign(sign, sign_profile)
    if sign_reading is None:
        return None
    return f"{sign_reading} {reading}" if sign_reading else reading


def render_signed_numeric(
    core: SignedNumericCore,
    *,
    sign_profile: SignProfile = SignProfile.DEFAULT,
    spaced_integer: bool = False,
) -> str | None:
    if not isinstance(core, SignedNumericCore):
        raise TypeError("core must be SignedNumericCore")
    reader = read_spaced_integer_text if spaced_integer else read_integer_text
    try:
        integer_reading = reader(core.integer_raw)
    except ValueError:
        return None
    if integer_reading is None:
        return None
    reading = apply_sign_profile(
        integer_reading,
        core.sign_kind,
        sign_profile=sign_profile,
    )
    if reading is None:
        return None
    if core.fractional_digits is None:
        return reading
    fractional = read_decimal_fraction_digits(core.fractional_digits)
    return f"{reading}쩜{fractional}"


__all__ = [
    "apply_sign_profile",
    "DEFAULT_SIGNED_OWNER_POLICY",
    "NumericCore",
    "SIGNED_OWNER_POLICIES",
    "SignKind",
    "SignProfile",
    "SignedNumericCore",
    "SignedOwnerPolicy",
    "parse_signed_numeric_core",
    "parse_sign_surface",
    "render_sign",
    "render_signed_numeric",
]
