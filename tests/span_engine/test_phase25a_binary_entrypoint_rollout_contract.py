from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


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


def test_phase25a_binary_entrypoint_mode_less_debug_contract(monkeypatch) -> None:
    module = _load_entrypoint_module()
    monkeypatch.setattr(
        sys,
        "argv",
        ["tts_preprocessor", "--text", "90km/h", "--include-debug"],
    )

    args = module.parse_args()

    assert args.text == "90km/h"
    assert args.include_debug is True
    assert not hasattr(args, "rollout_mode")


def test_phase25a_binary_entrypoint_rejects_removed_rollout_option(monkeypatch) -> None:
    module = _load_entrypoint_module()
    monkeypatch.setattr(
        sys,
        "argv",
        ["tts_preprocessor", "--rollout-mode", "span_default", "--text", "90km/h"],
    )

    with pytest.raises(SystemExit) as exc_info:
        module.parse_args()

    assert exc_info.value.code == 2
