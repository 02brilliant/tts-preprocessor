"""Phase 35C: Confirmed Gap Regression Tests.

This file contains **failing** regression tests for gaps confirmed in the
Phase 35B v1.0.1 Test/Policy Alignment Audit.

Current engine behavior (as of Phase 35C baseline) is documented inline for
each failing case so that Phase 35D hotfixes can reference the exact delta.

Scope:
  - Korean sentence embedded currency prefix symbols ($, €, ￥)
  - Prefix symbol + space currency full consume (€ 300, $ 300, ￦ 300)
  - Signed bare degree alignment (-2.5º)

Out of scope (policy-review / future – Phase 36):
  - 8.5m/min, 250m/L, 250m/l
  - 1,330원, 1,200건, 8,500명, 1,250m, 0.8초, 1.2km, 2,645.35선
  - 응급 신고는 112라고 적혀 있다

No implementation code was changed in Phase 35C.
No existing test expectations were modified.
"""

from __future__ import annotations

import pytest

from engine.span_engine import transform


# ---------------------------------------------------------------------------
# Gap 1: Korean sentence embedded currency prefix symbols
#
# Smoke observation (Phase 35B):
#   Input:  해외 가격표에는 $25.99, €1,234, ￥1,500이 나란히 적혀 있었다.
#   Current: 해외 가격표에는 $25.99, €1,234, 천오백 엔이 나란히 적혀 있었다.
#   Expected: 해외 가격표에는 이십오쩜구구 달러, 천이백삼십사 유로, 천오백 엔이 나란히 적혀 있었다.
#
# Root cause hypothesis:
#   $25.99 and €1,234 fail to transform inside a Korean sentence context
#   while ￥1,500 correctly transforms.  The all-Korean-lines fast path should
#   apply the full current engine transform to every token in the sentence.
# ---------------------------------------------------------------------------


def test_phase35c_embedded_multi_currency_prefix_symbols() -> None:
    """All three currency prefix symbols must transform within a Korean sentence."""
    text = "해외 가격표에는 $25.99, €1,234, ￥1,500이 나란히 적혀 있었다."
    expected = "해외 가격표에는 이십오쩜구구 달러, 천이백삼십사 유로, 천오백 엔이 나란히 적혀 있었다."
    # CURRENTLY FAILS:
    #   actual = '해외 가격표에는 $25.99, €1,234, 천오백 엔이 나란히 적혀 있었다.'
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # $ inside Korean sentence
        (
            "가격은 $25.99입니다.",
            "가격은 이십오쩜구구 달러입니다.",
        ),
        # € inside Korean sentence (bare, no decimal)
        (
            "비용은 €1,234입니다.",
            "비용은 천이백삼십사 유로입니다.",
        ),
        # ￥ inside Korean sentence (already passes per smoke, kept as regression guard)
        (
            "금액은 ￥1,500입니다.",
            "금액은 천오백 엔입니다.",
        ),
    ],
)
def test_phase35c_embedded_single_currency_in_korean_sentence(
    text: str, expected: str
) -> None:
    """Individual currency tokens must transform when embedded in a Korean sentence."""
    # The ￥ case likely already passes; the $ and € cases currently fail.
    assert transform(text) == expected


# ---------------------------------------------------------------------------
# Gap 2: Prefix symbol + space currency full consume
#
# Smoke observation (Phase 35B):
#   Input:  통화 검증 문단에는 € 300, $ 300, ￦ 300도 함께 넣는다.
#   Current: 통화 검증 문단에는 € 300, $ 300, ￦ 삼백도 함께 넣는다.
#   Expected: 통화 검증 문단에는 삼백 유로, 삼백 달러, 삼백 원도 함께 넣는다.
#
# Analysis:
#   - € 300 and $ 300: no transform at all (neither symbol nor number consumed).
#   - ￦ 300 → ￦ 삼백: partial rewrite – number converts but symbol is not
#     consumed.  This is a clear full-consume principle violation.
# ---------------------------------------------------------------------------


def test_phase35c_prefix_symbol_space_currency_full_consume() -> None:
    """Prefix symbol + space + amount must be fully consumed as a currency token."""
    text = "통화 검증 문단에는 € 300, $ 300, ￦ 300도 함께 넣는다."
    expected = "통화 검증 문단에는 삼백 유로, 삼백 달러, 삼백 원도 함께 넣는다."
    # CURRENTLY FAILS:
    #   actual = '통화 검증 문단에는 € 300, $ 300, ￦ 삼백도 함께 넣는다.'
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Standalone prefix-space currency forms
        ("€ 300", "삼백 유로"),
        ("$ 300", "삼백 달러"),
        ("￦ 300", "삼백 원"),
        ("€ 1,234", "천이백삼십사 유로"),
        ("$ 25.99", "이십오쩜구구 달러"),
    ],
)
def test_phase35c_standalone_prefix_symbol_space_currency(
    text: str, expected: str
) -> None:
    """Standalone prefix-symbol + space + amount must fully transform."""
    # CURRENTLY FAILS for all cases above.
    assert transform(text) == expected


def test_phase35c_won_space_amount_not_partial_rewrite() -> None:
    """￦ 300 must NOT produce '￦ 삼백' (partial rewrite is a full-consume violation)."""
    result = transform("￦ 300")
    # Assert the partial rewrite does NOT occur
    assert result != "￦ 삼백", (
        f"Partial rewrite detected: '￦ 300' -> {result!r}. "
        "Expected full consume to '삼백 원'."
    )
    # And that the correct full transform IS produced
    assert result == "삼백 원"


# ---------------------------------------------------------------------------
# Gap 3: Signed bare degree alignment
#
# Smoke observation (Phase 35B):
#   Input:  -2.5º
#   Current: -이쩜오º
#   Expected: 영하 이쩜오도
#
# Rationale:
#   25º → 이십오도  (already passes – bare º treated as 도)
#   -2.5ºC → 영하 이쩜오도  (already passes – signed Celsius)
#   -2.5ºF → 화씨 영하 이쩜오도  (already passes – signed Fahrenheit)
#   By policy parity, bare º with a negative sign should produce 영하 이쩜오도,
#   not the current malformed output '-이쩜오º'.
# ---------------------------------------------------------------------------


def test_phase35c_signed_bare_degree_alignment() -> None:
    """-2.5º must produce '영하 이쩜오도', consistent with -2.5ºC policy."""
    # CURRENTLY FAILS:
    #   actual = '-이쩜오º'
    assert transform("-2.5º") == "영하 이쩜오도"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Unsigned bare degree – regression guard (currently passes)
        ("25º", "이십오도"),
        # Signed Celsius – regression guard (currently passes)
        ("-2.5ºC", "영하 이쩜오도"),
        # Signed Fahrenheit – regression guard (currently passes)
        ("-2.5ºF", "화씨 영하 이쩜오도"),
    ],
)
def test_phase35c_degree_regression_guard(text: str, expected: str) -> None:
    """Adjacent degree cases must continue to pass throughout Phase 35C."""
    assert transform(text) == expected


# ---------------------------------------------------------------------------
# Preserve regression: currency unsafe tails
#
# These must pass now AND after Phase 35D hotfixes are applied.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("€abc", "€abc"),
        ("$abc", "$abc"),
        ("EURA 300", "EURA 300"),
        ("300EURabc", "300EURabc"),
        ("USDX 300", "USDX 300"),
        ("300KRWa", "300KRWa"),
        ("USB300", "USB300"),
        ("KRWabc", "KRWabc"),
    ],
)
def test_phase35c_currency_unsafe_tails_preserve(
    text: str, expected: str
) -> None:
    """Unsafe currency/code-like tails must be preserved exactly."""
    assert transform(text) == expected


# ---------------------------------------------------------------------------
# Preserve regression: temperature unsafe tails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2.5ºCat", "2.5ºCat"),
        ("30ºCtest", "30ºCtest"),
        ("40℉abc", "40℉abc"),
    ],
)
def test_phase35c_temperature_unsafe_tails_preserve(
    text: str, expected: str
) -> None:
    """Temperature tokens with unsafe tails must be preserved exactly."""
    assert transform(text) == expected
