from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[12.12 사태]", "12.12 사태"),
        ("사건은 [12.12 사태]입니다", "사건은 12.12 사태입니다"),
        ("[ -2.5 ]", " -2.5 "),
        ("[3kg]", "3kg"),
        ("[2025.01.03]", "2025.01.03"),
        ("[5·18 민주화운동]", "5·18 민주화운동"),
        ("[€1.25]", "€1.25"),
        ("[3.5~8kg]", "3.5~8kg"),
    ],
)
def test_square_bracket_protects_inner_text_and_unwraps_policy_v1(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "blocked_owners"),
    [
        ("[12.12 사태]", {"event", "decimal", "dotted_decimal_numeric"}),
        ("[2025.01.03]", {"date", "date_time.date", "decimal", "dotted_decimal_numeric"}),
        ("[3kg]", {"unit", "simple_unit"}),
        ("[$1.25]", {"currency", "decimal", "dotted_decimal_numeric"}),
        ("[€1.25]", {"currency", "decimal", "dotted_decimal_numeric"}),
        ("[3.5~8kg]", {"range", "unit", "decimal", "dotted_decimal_numeric"}),
    ],
)
def test_square_bracket_blocks_internal_owner_reentry_policy_v1(
    text: str, blocked_owners: set[str]
) -> None:
    output = transform_with_trace(text)

    assert not any(claim.owner in blocked_owners for claim in output.trace.claim_logs)
