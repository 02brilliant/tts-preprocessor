from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    "화씨 +77°F",
    "화씨 -77°F",
    "화씨 +77℉",
    "화씨 -77℉",
    "화씨 +1.5°F",
    "화씨 -0.0°F",
    "섭씨 +25°C",
    "섭씨 -25°C",
    "섭씨 +25℃",
    "섭씨 -25℃",
    "섭씨 +1.5°C",
    "섭씨 -0.0°C",
    "+77°F",
    "-77°F",
    "+25℃",
    "-25℃",
    "오늘 +77°F였다",
    "오늘 +25℃였다",
    "섭씨 +77°F",
    "화씨 +25°C",
    "`화씨 +77°F`",
    "/path/화씨+77°F/log",
    '{"temp":"화씨 +77°F"}',
    "보고서에는 화씨 +77°F, 섭씨 -3℃, 전화번호 +82-10-1234-5678, 화면비 16:9 화면비, multi-colon 값 1:2:3:4:5:6:7:8, 그리고 초과 블럭 1:2:3:4:5:6:7:8:9가 함께 포함되어 있다.",
    "오늘은 화씨 +77°F와 화씨 -10°F, 섭씨 +25°C와 섭씨 -3℃가 함께 표시되었고, standalone +77°F와 +25℃도 별도로 표시됐다.",
]


def main() -> None:
    for source in CASES:
        print(f"{source} -> {transform(source)}")


if __name__ == "__main__":
    main()
