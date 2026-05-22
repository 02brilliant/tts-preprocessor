from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    ("1：2 비율", "일 대 이 비율"),
    ("1：2테스트", "일 대 이 테스트"),
    ("1.5：2 비율", "일쩜오 대 이 비율"),
    ("1.5：2범위", "일쩜오 대 이 범위"),
    ("1：2：3", "일 대 이 대 삼"),
    ("1:2：3", "일 대 이 대 삼"),
    ("2：0으로 이겼다", "이 대 영으로 이겼다"),
    ("13：05에 시작", "십삼시 오분에 시작"),
    ("13：05", "13：05"),
    ("요한복음 3：16", "요한복음 3：16"),
    ("영상 1：23", "영상 1：23"),
    ("`1：2 비율`", "`1：2 비율`"),
    ("1–2개", "일에서 이 개"),
    ("1~2개", "일에서 이 개"),
    ("1～2개", "일에서 이 개"),
    ("1–2kg", "일에서 이 킬로그램"),
    ("1.5–2kg", "일쩜오에서 이 킬로그램"),
    ("1.5~2kg", "일쩜오에서 이 킬로그램"),
    ("1.5～2kg", "일쩜오에서 이 킬로그램"),
    ("1~2cm", "일에서 이 센티미터"),
    ("1–2테스트", "1–2테스트"),
    ("1~2테스트", "일에서 이 테스트"),
    ("1～2테스트", "일에서 이 테스트"),
    ("/path/1–2/log", "/path/1–2/log"),
    ("`1~2개`", "`1~2개`"),
]

NEIGHBOR_CASES = [
    ("1:2 비율과 25℃, $25.99, 3kg", "일 대 이 비율"),
    ("1：2 비율과 25℃, $25.99, 3kg", "일 대 이 비율"),
]


def main() -> None:
    failures: list[str] = []
    for source, expected in CASES:
        out = transform(source)
        if out != expected:
            failures.append(f"{source!r}\nEXPECTED={expected}\nOUT={out}")
    for source, semantic_pair in NEIGHBOR_CASES:
        out = transform(source)
        if (
            semantic_pair not in out
            or "이십오도" not in out
            or "이십오쩜구구 달러" not in out
            or "삼 킬로그램" not in out
        ):
            failures.append(f"neighbor failed: {source!r}\nOUT={out}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, failure in enumerate(failures[:100], 1):
            print("=" * 80)
            print("FAIL", index)
            print(failure)
        raise SystemExit(1)
    print("OK: no numeric delimiter equivalence failures")


if __name__ == "__main__":
    main()
