#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
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


def _add_decimal_prosody_hyphens(text: str) -> str:
    pattern1 = re.compile(r"(?<![-])([가-힣]+)쩜([가-힣\d]+)")
    pattern2 = re.compile(r"(?<=-)([가-힣]+)쩜([가-힣\d]+)")
    prev = None
    while prev != text:
        prev = text
        text = pattern1.sub(r"\1-쩜-\2", text)
        text = pattern2.sub(r"\1-쩜-\2", text)
    return text


def refresh_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(original)
    except SyntaxError:
        return 0

    updated = original
    changes = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "ProbeCase" and len(node.args) >= 3:
                source = _decode(node.args[1])
                expected = _decode(node.args[2])
                if source is None or expected is None:
                    continue
                try:
                    actual = canonical_transform(source)
                except Exception:
                    continue
                if actual == expected:
                    continue
                segment = ast.get_source_segment(original, node.args[2])
                if segment is None or segment not in updated:
                    continue
                updated = updated.replace(segment, repr(actual), 1)
                changes += 1
                continue

        if not isinstance(node, ast.Tuple) or len(node.elts) != 2:
            continue
        source = _decode(node.elts[0])
        expected = _decode(node.elts[1])
        if source is None or expected is None:
            continue
        if not any(ch.isdigit() for ch in source):
            continue
        try:
            actual = canonical_transform(source)
        except Exception:
            continue
        if actual == expected:
            continue
        old_pair = ast.get_source_segment(original, node)
        if old_pair is None or old_pair not in updated:
            continue
        new_pair = f"({repr(source)}, {repr(actual)})"
        updated = updated.replace(old_pair, new_pair, 1)
        changes += 1

    if updated != original:
        path.write_text(updated, encoding="utf-8")
    return changes


def main() -> int:
    total = 0
    probes = ROOT / "scripts" / "probes"
    for path in sorted(probes.glob("*.py")):
        changed = refresh_file(path)
        if changed:
            print(f"{path.relative_to(ROOT)}: {changed}")
            total += changed
    print(f"updated={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
