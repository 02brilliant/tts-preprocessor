from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_entrypoint_module():
    path = Path("bin/build_binary_entrypoint.py").resolve()
    spec = importlib.util.spec_from_file_location("phase25a_build_binary_entrypoint", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase25a_binary_entrypoint_module_importable() -> None:
    module = _load_entrypoint_module()
    assert callable(getattr(module, "parse_args"))
    assert callable(getattr(module, "run"))


def test_phase25a_binary_entrypoint_future_rollout_cli_contract(monkeypatch) -> None:
    module = _load_entrypoint_module()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tts_preprocessor",
            "--text",
            "90km/h",
            "--rollout-mode",
            "span_default",
            "--include-debug",
        ],
    )

    args = module.parse_args()

    assert getattr(args, "text") == "90km/h"
    assert getattr(args, "rollout_mode") == "span_default"
    assert getattr(args, "include_debug") is True

