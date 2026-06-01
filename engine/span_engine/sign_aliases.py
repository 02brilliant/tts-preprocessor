from __future__ import annotations

PLUS_SIGN = "+"

# Owner-local minus sign aliases for signed numeric-aware scanners. These
# characters are not normalized globally and are only meaningful when a scanner
# can full-claim the signed numeric surface.
MINUS_SIGN_ALIASES = frozenset({"-", "−", "－", "–", "—", "‒", "‑"})
SIGNED_NUMERIC_SIGN_ALIASES = frozenset({PLUS_SIGN, *MINUS_SIGN_ALIASES})


def is_signed_numeric_sign(value: str) -> bool:
    return value in SIGNED_NUMERIC_SIGN_ALIASES


def is_minus_sign_alias(value: str) -> bool:
    return value in MINUS_SIGN_ALIASES


def strip_signed_numeric_sign(value: str) -> tuple[str | None, str]:
    if not value:
        return None, value
    sign = value[0]
    if sign not in SIGNED_NUMERIC_SIGN_ALIASES:
        return None, value
    return sign, value[1:]
