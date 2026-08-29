from __future__ import annotations

import pytest

from engine.span_engine import transform_with_trace


def _claim_snapshot(text: str) -> tuple[str, list[tuple[str, str, str, int, int]]]:
    output = transform_with_trace(text)
    claims = [
        (
            claim.owner,
            claim.surface_type,
            claim.reason,
            claim.span.start,
            claim.span.end,
        )
        for claim in output.trace.claim_logs
    ]
    return output.normalized_text, claims


@pytest.mark.parametrize(
    ("text", "expected", "claim"),
    [
        (
            "1 ~ 2",
            "일에서 이",
            (
                "range",
                "RANGE_SURFACE",
                "tilde_numeric_range_broad_gate",
                0,
                5,
            ),
        ),
        (
            "3 kg",
            "삼-킬로그램",
            (
                "simple_unit",
                "SIMPLE_UNIT_SURFACE",
                "simple_unit_numeric_prefix",
                0,
                4,
            ),
        ),
        (
            "3 km/h",
            "시속 삼 킬로미터",
            (
                "compound_slash_unit",
                "COMPOUND_SLASH_UNIT_SURFACE",
                "compound_slash_unit_inventory_match",
                0,
                6,
            ),
        ),
        (
            "3 테스트",
            "삼 테스트",
            (
                "number",
                "NUMBER_SURFACE",
                "phase7_minimal_ascii_number",
                0,
                1,
            ),
        ),
    ],
)
def test_spaced_owner_deferral_and_number_fallback_contract(
    text: str,
    expected: str,
    claim: tuple[str, str, str, int, int],
) -> None:
    normalized, claims = _claim_snapshot(text)

    assert normalized == expected
    assert claims == [claim]


@pytest.mark.parametrize(
    ("text", "expected", "claims"),
    [
        (
            "3m/s",
            "초속 삼 미터",
            [
                (
                    "compound_slash_unit",
                    "COMPOUND_SLASH_UNIT_SURFACE",
                    "compound_slash_unit_inventory_match",
                    0,
                    4,
                )
            ],
        ),
        (
            "3cm/s",
            "초속 삼 센티미터",
            [
                (
                    "compound_slash_unit",
                    "COMPOUND_SLASH_UNIT_SURFACE",
                    "compound_slash_unit_inventory_match",
                    0,
                    5,
                )
            ],
        ),
        ("3kg/s", "3kg/s", []),
        (
            "3mph",
            "3mph",
            [
                (
                    "preserve",
                    "UNIT_CONTAMINATION_PRESERVE_SURFACE",
                    "unit_like_ascii_tail_contamination",
                    0,
                    4,
                )
            ],
        ),
    ],
)
def test_attached_unit_slash_and_contamination_remain_atomic(
    text: str,
    expected: str,
    claims: list[tuple[str, str, str, int, int]],
) -> None:
    assert _claim_snapshot(text) == (expected, claims)


def test_successful_earlier_owner_and_later_number_are_independent() -> None:
    assert _claim_snapshot("3 kg 테스트 4") == (
        "삼-킬로그램 테스트 사",
        [
            (
                "simple_unit",
                "SIMPLE_UNIT_SURFACE",
                "simple_unit_numeric_prefix",
                0,
                4,
            ),
            (
                "number",
                "NUMBER_SURFACE",
                "phase7_minimal_ascii_number",
                9,
                10,
            ),
        ],
    )


@pytest.mark.parametrize(
    ("text", "expected", "claims"),
    [
        ("01", "01", []),
        ("123abc", "123abc", []),
        (
            "https://example.com/123",
            "https://example.com/123",
            [
                (
                    "preserve",
                    "PROTECTED_LITERAL_SURFACE",
                    "url_path_email_code_protection_claim",
                    0,
                    23,
                )
            ],
        ),
        (
            "[123]",
            "123",
            [
                (
                    "bracket",
                    "PROTECTED_LITERAL_SURFACE",
                    "square_bracket_protection",
                    0,
                    5,
                )
            ],
        ),
        (
            "123입니다",
            "백이십삼입니다",
            [
                (
                    "number",
                    "NUMBER_SURFACE",
                    "phase7_minimal_ascii_number",
                    0,
                    3,
                )
            ],
        ),
    ],
)
def test_number_rejection_preserve_and_intended_fallback_boundaries(
    text: str,
    expected: str,
    claims: list[tuple[str, str, str, int, int]],
) -> None:
    assert _claim_snapshot(text) == (expected, claims)
