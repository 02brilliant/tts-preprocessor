from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected", "owner"),
    [
        ("3~8cm", "삼에서 팔 센티미터", "range_with_unit"),
        ("8cm", "팔 센티미터", "simple_unit"),
        ("3~8", "삼에서 팔", "range"),
        ("10~20%", "십에서 이십 퍼센트", "range_with_unit"),
        ("1~3㎏", "일에서 삼 킬로그램", "range_with_unit"),
    ],
)
def test_range_precedence_over_unit_counter_number(
    text: str, expected: str, owner: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert any(claim.owner == owner for claim in output.trace.claim_logs)
    if owner.startswith("range"):
        assert not any(claim.owner == "number" for claim in output.trace.claim_logs)


@pytest.mark.parametrize("text", ["$3~8", "3~$8"])
def test_unsupported_range_like_inputs_do_not_partial_claim(text: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert not any(claim.owner.startswith("range") for claim in output.trace.claim_logs)


def test_range_compatible_counter_suffix_claims_range() -> None:
    output = transform_with_trace("3~8명")

    assert output.normalized_text == "삼에서 팔 명"
    assert any(claim.owner == "range" for claim in output.trace.claim_logs)
