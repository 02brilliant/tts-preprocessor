from __future__ import annotations

import re

from .models import GateDecision, allow, deny


PURE_NUMERIC_MULTI_BLOCK_RE = re.compile(r"^\d{1,8}(?:-\d{1,8}){2,8}$")
PHONE_HYPHEN_RE = re.compile(r"^(?:010-\d{4}-\d{4}|02-\d{3}-\d{4}|\d{4}-\d{4})$")


def evaluate_hyphen_digit_blocks(
    *,
    candidate: str,
    **_: object,
) -> GateDecision:
    if PURE_NUMERIC_MULTI_BLOCK_RE.fullmatch(candidate) is None:
        return deny("hyphen candidate is not a pure numeric multi-block token")

    blocks = candidate.split("-")
    if len(blocks) < 3:
        return deny("two-block hyphen form is not owned by hyphen-digit-block stage", route="preserve")
    if len(blocks) > 9:
        return deny("hyphen block count exceeds documented routing range", route="preserve")
    if len(blocks) == 3 and [len(block) for block in blocks] == [4, 2, 2]:
        return allow("exact 4-2-2 form routes through date-priority hyphen stage", route="date_priority_digit_block")
    return allow("pure numeric hyphen multi-block routes through digit-block stage", route="digit_block")


def evaluate_hyphen_phone(
    *,
    candidate: str,
    **_: object,
) -> GateDecision:
    if PHONE_HYPHEN_RE.fullmatch(candidate) is None:
        return deny("hyphen candidate is not an exact phone form")
    return allow("exact phone hyphen form matched", route="phone")
