from __future__ import annotations

from engine.span_engine import TransformTrace, transform, transform_with_trace
from engine.span_engine.models import ValidationLog, ValidationResult


def test_transform_with_trace_runs_shadow_validation_for_pass_through_output() -> None:
    raw_text = "전문  가"
    output = transform_with_trace(raw_text)

    assert output.normalized_text == raw_text
    assert "".join(piece.text for piece in output.render_pieces) == raw_text
    assert isinstance(output.trace, TransformTrace)
    assert output.trace.validation_logs
    assert any(
        isinstance(log, ValidationLog) and log.passed is True
        for log in output.trace.validation_logs
    )
    assert transform(raw_text) == raw_text


def test_validation_models_have_independent_mutable_defaults() -> None:
    log1 = ValidationLog("KOREAN_LITERAL", True, "안녕", "안녕")
    log2 = ValidationLog("KOREAN_LITERAL", True)
    result1 = ValidationResult(True)
    result2 = ValidationResult(True)

    log1.metadata["x"] = 1
    result1.logs.append(log1)

    assert "x" not in log2.metadata
    assert result2.logs == []


def test_validation_model_accepts_log_list() -> None:
    log = ValidationLog("KOREAN_LITERAL", True, "안녕", "안녕")
    result = ValidationResult(True, [log])

    assert result.passed is True
    assert result.logs == [log]


def test_validation_model_rejects_non_bool_passed() -> None:
    try:
        ValidationLog("KOREAN_LITERAL", "yes")  # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        raise AssertionError("ValidationLog accepted non-bool passed")

    try:
        ValidationResult("yes")  # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        raise AssertionError("ValidationResult accepted non-bool passed")
