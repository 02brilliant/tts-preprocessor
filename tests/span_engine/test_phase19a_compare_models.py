from __future__ import annotations

import json

import pytest

from engine.span_engine.compare import COMPARE_CATEGORIES, CompareResult


def test_phase19a_compare_categories_contains_expected_values() -> None:
    assert COMPARE_CATEGORIES == {
        "same",
        "intended_v5_change",
        "suspicious_diff",
        "legacy_error_fixed",
        "unsupported",
    }


def test_phase19a_compare_result_defaults_are_independent() -> None:
    left = CompareResult(
        input_text="a",
        legacy_output="a",
        span_output="a",
        equal=True,
        category="same",
        reason="outputs_equal",
    )
    right = CompareResult(
        input_text="b",
        legacy_output="b",
        span_output="b",
        equal=True,
        category="same",
        reason="outputs_equal",
    )

    left.evidence["note"] = "x"
    assert right.evidence == {}


def test_phase19a_compare_result_is_json_serializable() -> None:
    result = CompareResult(
        input_text="3~8cm",
        legacy_output="3~8cm",
        span_output="삼에서 팔 센티미터",
        equal=False,
        category="intended_v5_change",
        reason="policy_allowlist",
        evidence={"policy_case": "3~8cm"},
        span_debug={"normalized_text": "삼에서 팔 센티미터"},
    )

    json.dumps(result.to_dict(), ensure_ascii=False)


def test_phase19a_compare_result_rejects_unknown_category() -> None:
    with pytest.raises(ValueError):
        CompareResult(
            input_text="x",
            legacy_output="x",
            span_output="x",
            equal=False,
            category="bad_category",
            reason="x",
        )


def test_phase19a_compare_result_equal_true_requires_same_category() -> None:
    with pytest.raises(ValueError):
        CompareResult(
            input_text="안녕하세요",
            legacy_output="안녕하세요",
            span_output="안녕하세요",
            equal=True,
            category="unsupported",
            reason="x",
        )
