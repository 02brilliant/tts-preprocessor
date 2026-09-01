from __future__ import annotations

import pytest

from engine.span_engine.transform import transform, transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("제5차", "제-오차"),
        ("제 5차", "제-오차"),
        ("제2", "제-이"),
        ("제 2", "제-이"),
        ('제2.5', '제-이-쩜-오'),
        ('제 2.5', '제-이-쩜-오'),
        ("제10년", "제-십년"),
        ("제 10년", "제-십년"),
        ('제2.5문항', '제-이-쩜-오문항'),
        ('제 2.5문항', '제-이-쩜-오문항'),
        ('제1.5가지', '제-일-쩜-오가지'),
        ("제3자abc", "제-삼자abc"),
        ("제2문항abc", "제-이문항abc"),
        ("제2문항A", "제-이문항A"),
        ("제 2문항abc", "제-이문항abc"),
        ("제10kg", "제십-킬로그램"),
        ("제10bp", "제십-베이시스 포인트"),
        ("제10bps", "제십 비피에스"),
        ("제 10kg", "제 십-킬로그램"),
        ("제 10bp", "제 십-베이시스 포인트"),
        ("제 10bps", "제 십 비피에스"),
        ("제 10 bps", "제 십 비피에스"),
    ],
)
def test_standalone_je_reads_number_as_sino(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("A제 5차", "A제 오차"),
        ("A제 2문항", "A제 두-문항"),
        ("A제 10년", "A제 십년"),
        ("한제 5차", "한제 오차"),
    ],
)
def test_glued_je_is_not_ordinal_and_following_number_follows_own_policy(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "A제5차",
        "A제10년",
        "A제2문항",
        "제5G",
        "제5abc",
        "제5-차",
        "제2-문항",
    ],
)
def test_attached_or_code_like_je_surfaces_still_preserve(source: str) -> None:
    assert transform(source) == source


def test_attached_latin_unit_after_je_uses_simple_unit_owner() -> None:
    output = transform_with_trace("제10kg")
    assert output.normalized_text == "제십-킬로그램"
    assert any(
        claim.owner == "simple_unit" and claim.reason == "simple_unit_numeric_prefix"
        for claim in output.trace.claim_logs
    )


def test_attached_bps_after_je_uses_compound_exact_unit_owner() -> None:
    output = transform_with_trace("제10bps")
    assert output.normalized_text == "제십 비피에스"
    assert any(
        claim.owner == "compound_exact_unit"
        and claim.reason == "compound_exact_unit_inventory_match"
        for claim in output.trace.claim_logs
    )
