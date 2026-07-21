from __future__ import annotations

import importlib
import inspect


def test_phase20f_binary_runtime_is_mode_less() -> None:
    binary_runtime = importlib.import_module("api.binary_runtime")

    assert not hasattr(binary_runtime, "run_transform_binary_with_rollout")
    assert "rollout_mode" not in inspect.signature(
        binary_runtime.run_transform_binary
    ).parameters
    assert "rollout_mode" not in inspect.signature(
        binary_runtime.run_transform_binary_debug
    ).parameters
