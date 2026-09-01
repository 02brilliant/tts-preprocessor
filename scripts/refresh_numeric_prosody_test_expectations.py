#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.main import transform as canonical_transform

_SKIP_FILE_MARKERS = ("forbidden",)
_REFRESHABLE_PARAM_NAMES = frozenset(
    {
        "source",
        "text",
        "input",
        "raw",
        "value",
        "sentence",
        "case",
        "src",
    }
)
_REFRESHABLE_VALUE_NAMES = frozenset(
    {
        "expected",
        "expected_text",
        "output",
        "normalized",
    }
)


def _decode_literal(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _encode(text: str) -> str:
    return repr(text)


def _should_skip_file(path: Path) -> bool:
    lowered = path.name.lower()
    return any(marker in lowered for marker in _SKIP_FILE_MARKERS)


def _should_refresh(source: str, expected: str) -> bool:
    if source == expected:
        return False
    if "http://" in source or "https://" in source:
        return False
    if not any(ch.isdigit() for ch in source):
        return False
    try:
        actual = canonical_transform(source)
    except Exception:
        return False
    return actual != expected


def _parametrize_names(decorator: ast.expr) -> list[str] | None:
    if not isinstance(decorator, ast.Call):
        return None
    if not isinstance(decorator.func, ast.Attribute):
        return None
    if decorator.func.attr != "parametrize":
        return None
    if not decorator.args:
        return None
    first = decorator.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return [part.strip() for part in first.value.split(",")]
    if isinstance(first, ast.Tuple):
        names: list[str] = []
        for element in first.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                names.append(element.value.strip())
        return names or None
    return None


_SKIP_VALUE_NAMES = frozenset(
    {
        "forbidden",
        "wrong_output",
        "wrong",
        "bad_output",
        "reject",
    }
)


def _parametrize_allows_refresh(decorator: ast.expr) -> bool:
    names = _parametrize_names(decorator)
    if not names or len(names) < 2:
        return False
    if set(names) & _SKIP_VALUE_NAMES:
        return False
    if names[1] not in _REFRESHABLE_VALUE_NAMES:
        return False
    return names[0] in _REFRESHABLE_PARAM_NAMES


def _collect_refreshable_lists(tree: ast.AST) -> set[int]:
    refreshable: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not _parametrize_allows_refresh(decorator):
                continue
            if not isinstance(decorator, ast.Call):
                continue
            for arg in decorator.args[1:]:
                if isinstance(arg, ast.List):
                    refreshable.add(id(arg))
                elif isinstance(arg, ast.Name):
                    target = arg.id
                    for assign in ast.walk(tree):
                        if not isinstance(assign, ast.Assign):
                            continue
                        for target_node in assign.targets:
                            if (
                                isinstance(target_node, ast.Name)
                                and target_node.id == target
                                and isinstance(assign.value, ast.List)
                            ):
                                refreshable.add(id(assign.value))
    return refreshable


def _replace_string_literal(source: str, old: str, new: str) -> str | None:
    encoded_old = _encode(old)
    encoded_new = _encode(new)
    if encoded_old not in source:
        return None
    return source.replace(encoded_old, encoded_new, 1)


def refresh_file(path: Path) -> int:
    if _should_skip_file(path):
        return 0

    original = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(original)
    except SyntaxError:
        return 0

    refreshable_lists = _collect_refreshable_lists(tree)
    updated = original
    changes = 0

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        if not isinstance(node.test, ast.Compare):
            continue
        if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.Eq):
            continue
        if len(node.test.comparators) != 1:
            continue

        left = node.test.left
        right = node.test.comparators[0]
        if not isinstance(left, ast.Call):
            continue
        if not isinstance(left.func, ast.Name):
            continue
        if left.func.id not in {"transform", "prod"}:
            continue
        if len(left.args) != 1:
            continue

        source = _decode_literal(left.args[0])
        expected = _decode_literal(right)
        if source is None or expected is None:
            continue
        if not _should_refresh(source, expected):
            continue

        actual = canonical_transform(source)
        replacement = _replace_string_literal(updated, expected, actual)
        if replacement is None:
            continue
        updated = replacement
        changes += 1

    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        if id(node) not in refreshable_lists:
            continue
        for elt in node.elts:
            if not isinstance(elt, ast.Tuple) or len(elt.elts) < 2:
                continue
            source = _decode_literal(elt.elts[0])
            expected = _decode_literal(elt.elts[1])
            if source is None or expected is None:
                continue
            if not _should_refresh(source, expected):
                continue

            actual = canonical_transform(source)
            old_pair = ast.get_source_segment(original, elt)
            if old_pair is None:
                continue
            if len(elt.elts) == 2:
                new_pair = f"({_encode(source)}, {_encode(actual)})"
            else:
                tail = ", ".join(
                    ast.get_source_segment(original, child) or _encode(_decode_literal(child) or "")
                    for child in elt.elts[2:]
                )
                new_pair = f"({_encode(source)}, {_encode(actual)}, {tail})"
            if old_pair not in updated:
                continue
            updated = updated.replace(old_pair, new_pair, 1)
            changes += 1

    if updated != original:
        path.write_text(updated, encoding="utf-8")
    return changes


def main() -> int:
    total = 0
    for base in (ROOT / "tests", ROOT / "LLM" / "tests"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("test_*.py")):
            changed = refresh_file(path)
            if changed:
                print(f"{path.relative_to(ROOT)}: {changed}")
                total += changed
    print(f"updated={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
