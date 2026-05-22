from __future__ import annotations

import importlib


def test_phase20f_future_binary_rollout_helper_span_default_contract() -> None:
    binary_runtime = importlib.import_module("api.binary_runtime")
    run_transform_binary_with_rollout = getattr(binary_runtime, "run_transform_binary_with_rollout")

    result = run_transform_binary_with_rollout(
        "90km/h",
        rollout_mode="span_default",
    )

    assert result == "시속 구십 킬로미터"
