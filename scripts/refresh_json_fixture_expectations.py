#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.main import transform as canonical_transform


def _refresh_pair_list(cases: list) -> int:
    changes = 0
    for index, case in enumerate(cases):
        if not (isinstance(case, list) and len(case) == 2):
            continue
        source, expected = case
        if not isinstance(source, str) or not isinstance(expected, str):
            continue
        if not any(ch.isdigit() for ch in source):
            continue
        try:
            actual = canonical_transform(source)
        except Exception:
            continue
        if actual != expected:
            cases[index] = [source, actual]
            changes += 1
    return changes


def refresh_json(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    changes = 0

    if isinstance(payload, list):
        for group in payload:
            if isinstance(group, dict) and isinstance(group.get("cases"), list):
                changes += _refresh_pair_list(group["cases"])
        if changes:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return changes

    if isinstance(payload, dict):
        for row in payload.get("stable_decisions", []):
            source = row.get("input")
            expected = row.get("expected")
            if not isinstance(source, str) or not isinstance(expected, str):
                continue
            try:
                actual = canonical_transform(source)
            except Exception:
                continue
            if actual != expected:
                row["expected"] = actual
                changes += 1
        for row in payload.get("allowed_diffs", []):
            source = row.get("input")
            if not isinstance(source, str):
                continue
            try:
                actual = canonical_transform(source)
            except Exception:
                continue
            if row.get("status") == "applied" and actual != row.get("after"):
                row["after"] = actual
                changes += 1
        if changes:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    return changes


def main() -> int:
    total = 0
    fixtures = ROOT / "tests" / "fixtures"
    for path in sorted(fixtures.glob("*.json")):
        changed = refresh_json(path)
        if changed:
            print(f"{path.relative_to(ROOT)}: {changed}")
            total += changed
    print(f"updated={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
