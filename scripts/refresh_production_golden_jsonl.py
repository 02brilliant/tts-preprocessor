#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.main import transform as canonical_transform


def main() -> int:
    path = ROOT / "tests" / "fixtures" / "production_golden.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    changes = 0
    updated_lines: list[str] = []
    for line in lines:
        if not line.strip():
            updated_lines.append(line)
            continue
        case = json.loads(line)
        source = case["input"]
        expected = case["expected"]
        try:
            actual = canonical_transform(source)
        except Exception:
            updated_lines.append(line)
            continue
        if actual != expected:
            case["expected"] = actual
            changes += 1
        updated_lines.append(json.dumps(case, ensure_ascii=False))
    if changes:
        path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print(f"updated={changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
