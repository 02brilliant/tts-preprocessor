from __future__ import annotations

from engine.span_engine.compare import build_span_debug, classify_compare_result


def test_phase19a_compare_classification_same() -> None:
    result = classify_compare_result(
        input_text="안녕하세요",
        legacy_output="안녕하세요",
        span_output="안녕하세요",
    )

    assert result.equal is True
    assert result.category == "same"
    assert result.reason == "outputs_equal"


def test_phase19a_compare_classification_intended_v5_change_range_with_unit() -> None:
    result = classify_compare_result(
        input_text="3~8cm",
        legacy_output="3~8cm",
        span_output="삼에서 팔 센티미터",
        span_debug=build_span_debug("3~8cm"),
    )

    assert result.equal is False
    assert result.category == "intended_v5_change"
    assert result.reason == "policy_allowlist"


def test_phase19a_compare_classification_intended_v5_change_date() -> None:
    result = classify_compare_result(
        input_text="2025-01-03",
        legacy_output="2025-01-03",
        span_output="이천이십오년 일월 삼일",
        span_debug=build_span_debug("2025-01-03"),
    )

    assert result.category == "intended_v5_change"


def test_phase19a_compare_classification_intended_v5_change_prosody_comma() -> None:
    result = classify_compare_result(
        input_text="그리고 우리는 결과를 확인했다",
        legacy_output="그리고 우리는 결과를 확인했다",
        span_output="그리고, 우리는 결과를 확인했다",
        span_debug=build_span_debug("그리고 우리는 결과를 확인했다"),
    )

    assert result.category == "intended_v5_change"


def test_phase19a_compare_classification_suspicious_literal_loss() -> None:
    result = classify_compare_result(
        input_text="안녕하세요",
        legacy_output="안녕하세요",
        span_output="안녕",
    )

    assert result.category == "suspicious_diff"
    assert result.reason == "changed_original_korean"


def test_phase19a_compare_classification_suspicious_bracket_protection() -> None:
    result = classify_compare_result(
        input_text="[3kg]",
        legacy_output="3kg",
        span_output="삼 킬로그램",
    )

    assert result.category == "suspicious_diff"
    assert result.reason == "bracket_protection"


def test_phase19a_compare_classification_suspicious_url_or_path_internal_change() -> None:
    result = classify_compare_result(
        input_text="http://x/90km/h",
        legacy_output="http://x/90km/h",
        span_output="http://x/시속 구십 킬로미터",
    )

    assert result.category == "suspicious_diff"
    assert result.reason == "url_or_path_internal_change"


def test_phase19a_compare_classification_span_error_is_suspicious() -> None:
    result = classify_compare_result(
        input_text="x",
        legacy_output="x",
        span_output=None,
        span_error="boom",
    )

    assert result.category == "suspicious_diff"
    assert result.reason == "span_error"


def test_phase19a_compare_classification_legacy_error_fixed() -> None:
    result = classify_compare_result(
        input_text="90km/h",
        legacy_output=None,
        span_output="시속 구십 킬로미터",
        legacy_error="legacy failed",
    )

    assert result.category == "legacy_error_fixed"
    assert result.reason == "legacy_error"


def test_phase19a_compare_classification_unsupported_fallback() -> None:
    result = classify_compare_result(
        input_text="미정 케이스",
        legacy_output="A",
        span_output="B",
    )

    assert result.category == "unsupported"
    assert result.reason == "unclassified_diff"
