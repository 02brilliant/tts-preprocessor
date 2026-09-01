#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.main import transform as canonical_transform

ROW_RE = re.compile(r"^(\|\s*`([^`]+)`\s*\|\s*)`([^`]+)`(\s*\|.*)$")


def main() -> int:
    path = ROOT / "docs" / "TTS_Preprocessor_numeric_matrix.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    section = ""
    updated = 0
    output_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            section = line[3:].strip()
        if section.startswith("11."):
            output_lines.append(line)
            continue
        match = ROW_RE.match(line)
        if match is None:
            output_lines.append(line)
            continue
        surface = match.group(2)
        doc_expected = match.group(3)
        if not any(ch.isdigit() for ch in surface):
            output_lines.append(line)
            continue
        try:
            actual = canonical_transform(surface)
        except Exception:
            output_lines.append(line)
            continue
        if actual == doc_expected:
            output_lines.append(line)
            continue
        output_lines.append(f"{match.group(1)}`{actual}`{match.group(4)}")
        updated += 1
    path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"updated_rows={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
