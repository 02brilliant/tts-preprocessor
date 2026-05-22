from __future__ import annotations

import ast
from pathlib import Path

from engine.span_engine import transform


SPAN_ENGINE_ROOT = Path(__file__).resolve().parents[2] / "engine" / "span_engine"
FORBIDDEN_IMPORT_PREFIXES = (
    "engine.pipeline",
    "engine.rules",
)
FORBIDDEN_REFERENCES = {
    "normalize_text",
    "transform_engine",
    "base_rules",
}


def _python_files() -> list[Path]:
    return sorted(SPAN_ENGINE_ROOT.rglob("*.py"))


def test_span_engine_package_exists() -> None:
    assert SPAN_ENGINE_ROOT.is_dir()
    assert _python_files()


def test_span_engine_does_not_import_legacy_pipeline_or_rules() -> None:
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
                assert not any(
                    name == prefix or name.startswith(f"{prefix}.")
                    for name in imported_names
                    for prefix in FORBIDDEN_IMPORT_PREFIXES
                ), f"Forbidden legacy import in {path}: {imported_names}"
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not any(
                    module == prefix or module.startswith(f"{prefix}.")
                    for prefix in FORBIDDEN_IMPORT_PREFIXES
                ), f"Forbidden legacy import in {path}: from {module}"


def test_span_engine_does_not_reference_legacy_normalize_or_rule_helpers() -> None:
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in FORBIDDEN_REFERENCES, (
                    f"Forbidden legacy reference in {path}: {node.id}"
                )
            elif isinstance(node, ast.Attribute):
                assert node.attr not in FORBIDDEN_REFERENCES, (
                    f"Forbidden legacy reference in {path}: {node.attr}"
                )


def test_span_engine_does_not_apply_legacy_acronym_behavior() -> None:
    assert transform("AI") == "에이아이"
    assert transform("AI이") == "에이아이이"
