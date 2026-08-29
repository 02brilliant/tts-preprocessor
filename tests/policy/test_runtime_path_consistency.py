from __future__ import annotations

import argparse
import ast
from pathlib import Path

import api.server as api_server
import bin.run_preprocessor as cli_entrypoint


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATHS = (
    PROJECT_ROOT / "api/server.py",
    PROJECT_ROOT / "api/binary_runtime.py",
    PROJECT_ROOT / "bin/run_preprocessor.py",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    return modules


def test_runtime_entrypoints_do_not_import_engine_sources():
    for path in RUNTIME_PATHS:
        imports = _imported_modules(path)
        assert not any(module == "engine" or module.startswith("engine.") for module in imports), (
            f"{path} imports engine sources directly: {sorted(imports)}"
        )
        assert not any(module == "LLM" or module.startswith("LLM.") for module in imports), (
            f"{path} imports LLM sources directly: {sorted(imports)}"
        )


def test_api_server_delegates_to_binary_runtime(monkeypatch):
    seen: list[str] = []

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return "__binary__"

    monkeypatch.setattr(api_server, "run_transform_binary", fake_run_transform_binary)

    result = api_server.transform_api(api_server.TransformRequest(text="서비스 경로"))
    assert result == {"normalized_text": "__binary__"}
    assert seen == ["서비스 경로"]


def test_api_server_validates_runtime_binary_on_startup(monkeypatch):
    seen: list[str] = []

    def fake_resolve_binary_path() -> Path:
        seen.append("resolved")
        return PROJECT_ROOT / "dist" / "tts_preprocessor"

    def fake_resolve_integrated_binary_path(level: int) -> Path:
        seen.append(f"resolved-{level}")
        return PROJECT_ROOT / "dist" / f"tts-preprocessor-level-{level}"

    def fake_resolve_simplified_binary_path() -> Path:
        seen.append("resolved-simplified")
        return PROJECT_ROOT / "dist" / "tts-preprocessor-simplified"

    def fake_uvicorn_run(*args, **kwargs) -> None:
        seen.append("uvicorn")

    monkeypatch.setattr(api_server, "resolve_binary_path", fake_resolve_binary_path)
    monkeypatch.setattr(
        api_server,
        "resolve_simplified_binary_path",
        fake_resolve_simplified_binary_path,
    )
    monkeypatch.setattr(
        api_server,
        "resolve_integrated_binary_path",
        fake_resolve_integrated_binary_path,
    )
    monkeypatch.setattr(api_server.uvicorn, "run", fake_uvicorn_run)

    api_server.main()

    assert seen == [
        "resolved",
        "resolved-simplified",
        "resolved-3",
        "resolved-4",
        "uvicorn",
    ]


def test_cli_wrapper_delegates_to_binary_runtime(monkeypatch, capsys):
    seen: list[str] = []

    monkeypatch.setattr(
        cli_entrypoint,
        "parse_args",
        lambda: argparse.Namespace(input=None, output=None, text="CLI 경로"),
    )

    def fake_run_transform_binary(text: str) -> str:
        seen.append(text)
        return "__cli-binary__"

    monkeypatch.setattr(cli_entrypoint, "run_transform_binary", fake_run_transform_binary)

    assert cli_entrypoint.run() == 0
    assert seen == ["CLI 경로"]
    assert capsys.readouterr().out.strip() == "__cli-binary__"


def test_cli_wrapper_writes_binary_output_to_file(monkeypatch, tmp_path):
    output_path = tmp_path / "output.txt"

    monkeypatch.setattr(
        cli_entrypoint,
        "parse_args",
        lambda: argparse.Namespace(input=None, output=str(output_path), text="파일 출력"),
    )
    monkeypatch.setattr(cli_entrypoint, "run_transform_binary", lambda text: "__file__")

    assert cli_entrypoint.run() == 0
    assert output_path.read_text(encoding="utf-8") == "__file__"
