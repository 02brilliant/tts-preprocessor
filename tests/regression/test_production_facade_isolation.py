from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.binary_runtime as binary_runtime
import api.server as api_server
import engine.main as engine_main
from tests._production_boundary import unexpected_binary_modules


UNSUPPORTED_ROLLOUT_VALUES = ("retired_mode", "unsupported_mode")


def _load_binary_entrypoint():
    path = Path("bin/build_binary_entrypoint.py").resolve()
    spec = importlib.util.spec_from_file_location(
        "production_facade_binary_entrypoint",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_production_facade_is_mode_less() -> None:
    assert tuple(inspect.signature(engine_main.transform).parameters) == ("text",)
    assert tuple(inspect.signature(engine_main.transform_debug).parameters) == ("text",)


def test_engine_main_exports_default_and_simplified_production_facades() -> None:
    assert engine_main.__all__ == [
        "transform",
        "transform_debug",
        "transform_simplified",
        "transform_simplified_debug",
    ]
    public_names = {name for name in vars(engine_main) if not name.startswith("_")}
    assert all("rollout" not in name for name in public_names)
    assert not hasattr(importlib.import_module("engine.api_interface"), "normalize_text_with_rollout")
    assert not hasattr(binary_runtime, "run_transform_binary_with_rollout")
    adapter = importlib.import_module("engine.span_engine.production_adapter")
    assert not hasattr(adapter, "run_rollout_transform")
    assert not hasattr(adapter, "run_rollout_payload")
    assert not hasattr(adapter, "normalize_rollout_mode")


def test_production_adapter_exposes_only_the_current_facade() -> None:
    adapter = importlib.import_module("engine.span_engine.production_adapter")

    assert adapter.__all__ == ["transform_for_production"]
    assert tuple(inspect.signature(adapter.transform_for_production).parameters) == (
        "text",
        "debug",
    )
    assert not hasattr(adapter, "transform_payload")
    assert adapter.transform_for_production("90km/h") == "시속 구십 킬로미터"
    debug = adapter.transform_for_production("90km/h", debug=True)
    assert debug["ok"] is True
    assert debug["normalized_text"] == "시속 구십 킬로미터"


def test_binary_debug_runtime_never_falls_back_to_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd, *, input, capture_output, text, check):
        assert cmd == ["/tmp/fake-binary", "--include-debug"]
        return SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="unrecognized arguments: --include-debug",
        )

    monkeypatch.setattr(
        binary_runtime,
        "resolve_binary_path",
        lambda: Path("/tmp/fake-binary"),
    )
    monkeypatch.setattr(binary_runtime.subprocess, "run", fake_run)

    with pytest.raises(
        binary_runtime.BinaryRuntimeError,
        match="unrecognized arguments: --include-debug",
    ):
        binary_runtime.run_transform_binary_debug("90km/h")

    assert not hasattr(binary_runtime, "SOURCE_DEBUG_FALLBACK_ENV")
    assert not hasattr(binary_runtime, "_run_source_debug_fallback")


def test_binary_entrypoint_has_no_rollout_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_binary_entrypoint()
    monkeypatch.setattr(
        sys,
        "argv",
        ["tts_preprocessor", "--text", "90km/h", "--rollout-mode", "span_default"],
    )
    with pytest.raises(SystemExit) as exc_info:
        module.parse_args()
    assert exc_info.value.code == 2


def test_binary_entrypoint_keeps_mode_less_debug_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_binary_entrypoint()
    monkeypatch.setattr(
        sys,
        "argv",
        ["tts_preprocessor", "--text", "90km/h", "--include-debug"],
    )

    args = module.parse_args()

    assert not hasattr(args, "rollout_mode")
    assert args.include_debug is True


@pytest.mark.parametrize("mode", UNSUPPORTED_ROLLOUT_VALUES)
def test_api_payload_rejects_removed_rollout_field_before_binary_execution(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("unsupported rollout field reached the production binary")

    monkeypatch.setattr(api_server, "run_transform_binary", fail_if_called)
    monkeypatch.setattr(api_server, "run_transform_binary_debug", fail_if_called)

    with pytest.raises(ValueError, match="not supported"):
        api_server.transform_request_payload(
            {"text": "90km/h", "rollout_mode": mode},
        )


def test_source_production_import_graph_contains_only_current_modules() -> None:
    probe = r"""
import json
import sys

from engine.main import transform, transform_debug

for source in (
    "01명",
    "09시",
    "1만3천여 명",
    "123 · 456",
    "2~5시",
    "회의는 2025-01-03 13:05에 시작한다.",
):
    transform(source)

debug_result = transform_debug("90km/h")
assert debug_result["normalized_text"] == "시속 구십 킬로미터"

loaded = sorted(name for name in sys.modules if name.startswith("engine."))
print(json.dumps(loaded))
"""
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    loaded_modules = json.loads(result.stdout)
    assert unexpected_binary_modules(loaded_modules) == []


def test_prosody_package_exports_no_insert_commas() -> None:
    prosody = importlib.import_module("engine.prosody")

    assert not hasattr(prosody, "insert_commas")


def test_pyinstaller_config_uses_current_dependency_closure() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    build_paths = (
        root_dir / "scripts" / "build_binary.sh",
        root_dir / "scripts" / "build_remote_package.sh",
        root_dir / ".github" / "workflows" / "build-desktop-executables.yml",
        root_dir / "docs" / "deployment_runbook.md",
    )
    build_configs = {path: path.read_text(encoding="utf-8") for path in build_paths}
    deploy_script = (root_dir / "scripts" / "deploy_server.sh").read_text(encoding="utf-8")
    spec = (root_dir / "tts_preprocessor.spec").read_text(encoding="utf-8")

    for path, config in build_configs.items():
        assert "--collect-submodules engine" not in config, path
        assert "tts_preprocessor.spec" in config, path
    assert "tts_preprocessor.spec" in deploy_script
    assert "collect_submodules" not in spec
    assert "hiddenimports=[]" in spec
    assert "datas=[]" in spec
    assert "excludes=[]" in spec
    assert "runtime_hooks=[]" in spec
    assert "pyinstaller_runtime_hooks" not in spec
