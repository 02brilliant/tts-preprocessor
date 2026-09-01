#!/usr/bin/env python3
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.main import transform as canonical_transform


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
        return [
            element.value.strip()
            for element in first.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        ] or None
    return None


def _decode(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _encode(text: str) -> str:
    return repr(text)


def _forbidden_cases(tree: ast.AST) -> dict[str, str]:
    cases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            names = _parametrize_names(decorator)
            if not names or "forbidden" not in names:
                continue
            text_index = names.index(names[0])
            forbidden_index = names.index("forbidden")
            if not isinstance(decorator, ast.Call):
                continue
            lists: list[ast.List] = []
            for arg in decorator.args[1:]:
                if isinstance(arg, ast.List):
                    lists.append(arg)
                elif isinstance(arg, ast.Name):
                    var = arg.id
                    for assign in ast.walk(tree):
                        if not isinstance(assign, ast.Assign):
                            continue
                        for target in assign.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == var
                                and isinstance(assign.value, ast.List)
                            ):
                                lists.append(assign.value)
            for case_list in lists:
                for elt in case_list.elts:
                    if not isinstance(elt, ast.Tuple):
                        continue
                    if len(elt.elts) <= max(text_index, forbidden_index):
                        continue
                    text = _decode(elt.elts[text_index])
                    forbidden = _decode(elt.elts[forbidden_index])
                    if text is None or forbidden is None:
                        continue
                    cases[text] = forbidden
    return cases


def _git_source(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{path.relative_to(ROOT)}"],
            cwd=ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None


def restore_file(path: Path) -> int:
    git_source = _git_source(path)
    if git_source is None:
        return 0

    current_source = path.read_text(encoding="utf-8")
    try:
        current_tree = ast.parse(current_source)
        git_tree = ast.parse(git_source)
    except SyntaxError:
        return 0

    git_cases = _forbidden_cases(git_tree)
    if not git_cases:
        return 0

    updated = current_source
    changes = 0
    for text, git_forbidden in git_cases.items():
        try:
            actual = canonical_transform(text)
        except Exception:
            continue
        current_forbidden = None
        for node in ast.walk(current_tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                names = _parametrize_names(decorator)
                if not names or "forbidden" not in names:
                    continue
                forbidden_index = names.index("forbidden")
                text_index = 0
                if not isinstance(decorator, ast.Call):
                    continue
                for arg in decorator.args[1:]:
                    lists = [arg] if isinstance(arg, ast.List) else []
                    if isinstance(arg, ast.Name):
                        var = arg.id
                        for assign in ast.walk(current_tree):
                            if isinstance(assign, ast.Assign):
                                for target in assign.targets:
                                    if (
                                        isinstance(target, ast.Name)
                                        and target.id == var
                                        and isinstance(assign.value, ast.List)
                                    ):
                                        lists.append(assign.value)
                    for case_list in lists:
                        for elt in getattr(case_list, "elts", []):
                            if not isinstance(elt, ast.Tuple):
                                continue
                            if len(elt.elts) <= forbidden_index:
                                continue
                            case_text = _decode(elt.elts[text_index])
                            if case_text != text:
                                continue
                            current_forbidden = _decode(elt.elts[forbidden_index])
        if current_forbidden is None or current_forbidden == git_forbidden:
            continue
        if current_forbidden != actual:
            continue
        old = _encode(current_forbidden)
        new = _encode(git_forbidden)
        if old not in updated:
            continue
        updated = updated.replace(old, new, 1)
        changes += 1

    if updated != current_source:
        path.write_text(updated, encoding="utf-8")
    return changes


def main() -> int:
    total = 0
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        changed = restore_file(path)
        if changed:
            print(f"{path.relative_to(ROOT)}: {changed}")
            total += changed
    print(f"restored={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
