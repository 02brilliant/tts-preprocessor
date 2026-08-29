from __future__ import annotations

import importlib

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("45m²", "사십오-제곱미터"),
        ("x²", "x²"),
        ("A²B", "A²B"),
        ("25℃", "이십오도"),
        ("25℉", "화씨 이십오도"),
        ("7시간 05분", "일곱-시간 오분"),
        ("3시간 18분", "세-시간 십팔분"),
        ("2.5%p", "이쩜오-퍼센트포인트"),
        ("-2.5%p", "마이너스 이쩜오-퍼센트포인트"),
        ("1/3", "삼분의 일"),
        ("-1/3", "마이너스 삼분의 일"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("pH 7.4", "피에이치 칠쩜사"),
        ("12.3 비상계엄", "십이삼 비상계엄"),
    ],
)
def test_phase34c_known_expected_regression(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "①②③",
        "１２３",
        "⅓",
        "1,23,456원",
        "12,34/56",
        "1/0",
        "0/3",
        "1 / 3",
        "pH7.4test",
        "A-2.5℃",
        "🚨 119 ☃ 45m²",
        "abc€",
        "€abc",
        "$abc",
        "5Hzabc",
        "2.5%pa",
        "1,23%p",
        "1,23시간",
        "1,23/456",
        "12 · 3",
        "12. 3",
        "12 .3",
        "45m²abc",
        "45m³abc",
    ],
)
def test_phase34c_weird_inputs_do_not_raise(text: str) -> None:
    output = transform(text)

    assert isinstance(output, str)
    if text:
        assert output


def test_phase34c_public_transform_recovers_hangul_input_by_segment(monkeypatch) -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")

    def fail_transform_with_trace(_: str):
        raise RuntimeError("simulated internal parser failure")

    monkeypatch.setattr(
        transform_module,
        "transform_with_trace",
        fail_transform_with_trace,
    )

    assert transform_module.transform("45m² fallback 대상") == "사십오-제곱미터 fallback 대상"


def test_phase34c_debug_path_records_segment_fallback_metadata(monkeypatch) -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    def fail_transform_with_trace(_: str):
        raise RuntimeError("simulated internal parser failure")

    monkeypatch.setattr(
        adapter,
        "transform_with_trace",
        fail_transform_with_trace,
    )

    result = adapter.transform_for_production("45m² debug 대상", debug=True)

    assert result["ok"] is True
    assert result["normalized_text"] == "사십오-제곱미터 debug 대상"
    assert result["fallback"] == "segment_preserve"
    assert result["error_type"] == "RuntimeError"
    assert result["error_stage"] == "transform"
    assert result["debug"]["fallback"] == "segment_preserve"


def test_phase34c_engine_main_mode_less_error_result_recovers_segments(monkeypatch) -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    engine_main = importlib.import_module("engine.main")

    def fail_transform(_: str) -> str:
        raise RuntimeError("simulated internal parser failure")

    monkeypatch.setattr(adapter, "transform", fail_transform)

    assert engine_main.transform("45m² engine 대상") == "사십오-제곱미터 engine 대상"

def test_phase34c_internal_failure_preserves_only_failed_source_segment(
    monkeypatch,
) -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")
    original_core = transform_module._transform_core_with_trace

    def fail_selected_segment(text: str):
        if "FAIL구간" in text:
            raise RuntimeError("selected segment failure")
        return original_core(text)

    monkeypatch.setattr(
        transform_module,
        "_transform_core_with_trace",
        fail_selected_segment,
    )

    text = "45m² 정상 FAIL구간 60Hz 자료"
    output = transform_module.transform_with_trace(text)

    assert output.normalized_text == "사십오-제곱미터 정상 FAIL구간 육십-헤르츠 자료"
    fallback_log = output.trace.fallback_logs[0]
    failures = fallback_log.metadata["segment_failures"]
    failed_start = text.index("FAIL구간")
    assert failures == [
        {
            "start": failed_start,
            "end": failed_start + len("FAIL구간"),
            "error_type": "RuntimeError",
            "error_message": "selected segment failure",
        }
    ]
    assert any(
        piece.text == "FAIL구간"
        and piece.provenance == "ORIGINAL_BOUNDARY"
        and piece.source_span.start == failed_start
        and piece.source_span.end == failed_start + len("FAIL구간")
        for piece in output.render_pieces
    )
    assert any(
        piece.text == "육십-헤르츠"
        and piece.owner == "simple_unit"
        for piece in output.render_pieces
    )


def test_phase34c_whole_input_preserve_policy_is_explicit() -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")

    assert transform_module.may_whole_input_preserve(
        "ASCII only", "global_no_hangul_bypass"
    )
    assert transform_module.may_whole_input_preserve(
        "전체보존", "whole_input_absolute_preserve"
    )
    assert not transform_module.may_whole_input_preserve(
        "한글 포함", "global_no_hangul_bypass"
    )
