from __future__ import annotations

import ast
from pathlib import Path

from engine.span_engine import transform


SPAN_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "engine" / "span_engine"
ALLOWED_EXTERNAL_ENGINE_IMPORTS = {"engine.prosody.paragraph"}


def _python_files() -> list[Path]:
    return sorted(SPAN_ENGINE_ROOT.rglob("*.py"))


def test_span_engine_package_exists() -> None:
    assert SPAN_ENGINE_ROOT.is_dir()
    assert _python_files()


def test_span_engine_imports_only_current_engine_graph() -> None:
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        unexpected = sorted(
            module
            for module in imported_modules
            if module.startswith("engine.")
            and not module.startswith("engine.span_engine")
            and module not in ALLOWED_EXTERNAL_ENGINE_IMPORTS
        )
        assert unexpected == [], (path, unexpected)


def test_span_engine_applies_current_acronym_behavior() -> None:
    assert transform("AI") == "에이아이"
    assert transform("AI이") == "에이아이이"
