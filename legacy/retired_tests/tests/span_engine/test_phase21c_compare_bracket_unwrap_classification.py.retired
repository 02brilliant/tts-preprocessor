from __future__ import annotations

from engine.span_engine.compare import CompareCorpusEntry, classify_compare_result, run_compare_corpus


def test_phase21c_bracket_final_unwrap_should_be_classified_as_intended() -> None:
    result = classify_compare_result(
        input_text="[3kg]",
        legacy_output="[3kg]",
        span_output="3kg",
    )

    assert result.category == "intended_v5_change"
    assert result.reason in {"policy_allowlist", "final_bracket_filter_intended", "square_bracket_final_unwrap"}


def test_phase21c_bracket_corpus_expected_category_should_override_suspicious_heuristic() -> None:
    entry = CompareCorpusEntry(
        id="bracket-unit",
        text="[3kg]",
        tags=("bracket", "intended_diff"),
        expected_category="intended_v5_change",
    )

    report = run_compare_corpus([entry], legacy_transform=lambda text: text)
    result = report.results[0]

    assert result.category == "intended_v5_change"
    assert result.evidence.get("expected_category_mismatch") is not True


def test_phase21c_bracket_internal_rewrite_must_remain_suspicious() -> None:
    result = classify_compare_result(
        input_text="[3kg]",
        legacy_output="[3kg]",
        span_output="삼 킬로그램",
    )

    assert result.category == "suspicious_diff"
