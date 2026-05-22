from __future__ import annotations

from engine.span_engine.compare import classify_compare_result


def test_phase22c_bracket_internal_rewrite_must_remain_suspicious() -> None:
    result = classify_compare_result(
        input_text="[3kg]",
        legacy_output="[3kg]",
        span_output="삼 킬로그램",
    )

    assert result.category == "suspicious_diff"


def test_phase22c_malformed_bracket_should_not_be_implicitly_allowlisted() -> None:
    result = classify_compare_result(
        input_text="[3kg",
        legacy_output="삼 킬로그램",
        span_output="3kg",
    )

    assert result.category == "suspicious_diff"
