from __future__ import annotations

import importlib

from engine.span_engine.compare import classify_compare_result


def test_phase22c_actual_legacy_bracket_should_be_classified_as_intended_after_policy_fix() -> None:
    result = classify_compare_result(
        input_text="[3kg]",
        legacy_output="삼 킬로그램",
        span_output="3kg",
    )

    assert result.category == "intended_v5_change"
    assert result.evidence.get("rule") in {
        "legacy_bracket_internal_normalization",
        "legacy_behavior_changed_by_policy",
        "legacy_bracket_internal_normalization_v5_protected_unwrap",
        "square_bracket_final_unwrap",
    }


def test_phase22c_actual_legacy_bracket_corpus_entry_should_be_intended_after_policy_fix() -> None:
    compare_module = importlib.import_module("engine.span_engine.compare")
    CompareCorpusEntry = getattr(compare_module, "CompareCorpusEntry")
    run_compare_corpus = getattr(compare_module, "run_compare_corpus")

    entry = CompareCorpusEntry(
        id="bracket-unit",
        text="[3kg]",
        tags=("bracket", "preserve", "intended_diff"),
        expected_category="intended_v5_change",
    )

    report = run_compare_corpus([entry], legacy_transform=lambda text: "삼 킬로그램")
    result = report.results[0]

    assert result.category == "intended_v5_change"
    assert result.evidence.get("expected_category_mismatch") is not True
