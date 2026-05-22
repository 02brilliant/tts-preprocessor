from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    "+1 올랐다",
    "오차는 +0.05다",
    "+1.5kg",
    "-25kg",
    "+25℃",
    "+25°C",
    "+77℉",
    "+77°F",
    "+10%",
    "+1,000원",
    "+3.50달러",
    "+82-10-1234-5678",
    "+1:2 비율",
    "1:+2 비율",
    "+1:2:3",
    "+1:02:03",
    "+1.5~+2.0kg",
    "+1.5-2kg",
    "+.5",
    "C++17",
    "email+tag@example.com",
    "https://example.com?q=+1",
    "/path/+1/log",
    "`+1.5kg`",
]


def main() -> None:
    for source in CASES:
        print(f"{source} -> {transform(source)}")


if __name__ == "__main__":
    main()
