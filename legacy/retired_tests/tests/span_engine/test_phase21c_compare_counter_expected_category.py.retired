from __future__ import annotations

from engine.span_engine.compare import CompareCorpusEntry, classify_compare_result, run_compare_corpus


def test_phase21c_counter_expected_category_should_override_changed_original_korean() -> None:
    entry = CompareCorpusEntry(
        id="counter-21",
        text="21명",
        tags=("counter", "intended_diff"),
        expected_category="intended_v5_change",
    )

    report = run_compare_corpus([entry], legacy_transform=lambda text: text)
    result = report.results[0]

    assert result.category == "intended_v5_change"
    assert result.evidence.get("expected_category_mismatch") is not True


def test_phase21c_counter_direct_classification_should_be_intended() -> None:
    result = classify_compare_result(
        input_text="21명",
        legacy_output="21명",
        span_output="스물한 명",
    )

    assert result.category == "intended_v5_change"


def test_phase21c_counter_korean_literal_loss_should_stay_suspicious() -> None:
    result = classify_compare_result(
        input_text="전문가 유지",
        legacy_output="전문가 유지",
        span_output="전문이 유지",
    )

    assert result.category == "suspicious_diff"
