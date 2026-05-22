from __future__ import annotations

import importlib

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("45m²", "사십오 제곱미터"),
        ("x²", "x²"),
        ("A²B", "A²B"),
        ("25℃", "이십오도"),
        ("25℉", "화씨 이십오도"),
        ("7시간 05분", "일곱 시간 오분"),
        ("3시간 18분", "세 시간 십팔분"),
        ("2.5%p", "이쩜오 퍼센트포인트"),
        ("-2.5%p", "마이너스 이쩜오 퍼센트포인트"),
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


def test_phase34c_public_transform_falls_back_to_original_text(monkeypatch) -> None:
    transform_module = importlib.import_module("engine.span_engine.transform")

    def fail_transform_with_trace(_: str):
        raise RuntimeError("simulated internal parser failure")

    monkeypatch.setattr(
        transform_module,
        "transform_with_trace",
        fail_transform_with_trace,
    )

    assert transform_module.transform("fallback 대상") == "fallback 대상"


def test_phase34c_debug_path_records_fallback_metadata(monkeypatch) -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    def fail_transform_with_trace(_: str):
        raise RuntimeError("simulated internal parser failure")

    monkeypatch.setattr(
        adapter,
        "transform_with_trace",
        fail_transform_with_trace,
    )

    result = adapter.transform_for_production("debug fallback", debug=True)

    assert result["ok"] is True
    assert result["normalized_text"] == "debug fallback"
    assert result["fallback"] == "preserve_original"
    assert result["error_type"] == "RuntimeError"
    assert result["error_stage"] == "transform"
    assert result["debug"]["fallback"] == "preserve_original"


def test_phase34c_engine_main_span_default_error_result_falls_back(monkeypatch) -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    engine_main = importlib.import_module("engine.main")

    def fake_run_rollout_transform(
        text: str,
        *,
        mode: str,
        legacy_transform=None,
        include_debug: bool = False,
    ):
        return {
            "ok": False,
            "mode": "span_default",
            "input_text": text,
            "normalized_text": None,
            "production_output": None,
            "span_output": None,
            "compare": None,
            "error": "simulated internal parser failure",
        }

    monkeypatch.setattr(adapter, "run_rollout_transform", fake_run_rollout_transform)

    assert engine_main.transform_with_rollout("engine fallback", mode="span_default") == "engine fallback"
    debug_result = engine_main.transform_with_rollout(
        "engine fallback",
        mode="span_default",
        include_debug=True,
    )
    assert debug_result["normalized_text"] == "engine fallback"
    assert debug_result["fallback"] == "preserve_original"
    assert debug_result["error_stage"] == "transform"


def test_phase34c_invalid_rollout_mode_remains_operational_error() -> None:
    engine_main = importlib.import_module("engine.main")

    with pytest.raises(ValueError):
        engine_main.transform_with_rollout("AI", mode="invalid")
