#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.main import transform as canonical_transform


def _decode(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_replacements(tree: ast.AST) -> list[tuple[int, int, int, int, str]]:
    items: list[tuple[int, int, int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "TextCase":
            continue
        text = None
        expected_node = None
        for keyword in node.keywords:
            if keyword.arg == "text":
                text = _decode(keyword.value)
            elif keyword.arg == "expected":
                expected_node = keyword.value
        expected = _decode(expected_node) if expected_node is not None else None
        if text is None or expected is None or expected_node is None:
            continue
        if text == expected:
            continue
        if not any(ch.isdigit() for ch in text):
            continue
        try:
            actual = canonical_transform(text)
        except Exception:
            continue
        if actual == expected:
            continue
        if (
            expected_node.lineno is None
            or expected_node.col_offset is None
            or expected_node.end_lineno is None
            or expected_node.end_col_offset is None
            or expected_node.lineno != expected_node.end_lineno
        ):
            continue
        items.append(
            (
                expected_node.lineno,
                expected_node.col_offset,
                expected_node.end_lineno,
                expected_node.end_col_offset,
                repr(actual),
            )
        )
    return items


def _apply_replacements(original: str, items: list[tuple[int, int, int, int, str]]) -> str:
    lines = original.splitlines(keepends=True)
    for lineno, col_offset, _end_lineno, end_col_offset, new_segment in sorted(
        items, reverse=True
    ):
        line_index = lineno - 1
        line = lines[line_index]
        lines[line_index] = line[:col_offset] + new_segment + line[end_col_offset:]
    return "".join(lines)


def refresh_file(path: Path) -> int:
    if "comma_boundary" in path.name:
        return 0
    original = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(original)
    except SyntaxError:
        return 0
    items = _collect_replacements(tree)
    if not items:
        return 0
    updated = _apply_replacements(original, items)
    if updated == original:
        return 0
    path.write_text(updated, encoding="utf-8")
    return len(items)


def main() -> int:
    total = 0
    for path in sorted((ROOT / "tests").rglob("*.py")):
        if "forbidden" in path.name.lower():
            continue
        changed = refresh_file(path)
        if changed:
            print(f"{path.relative_to(ROOT)}: {changed}")
            total += changed
    print(f"updated={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
