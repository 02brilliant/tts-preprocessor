from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    ("1~2테스트", "일에서 이 테스트"),
    ("1～2테스트", "일에서 이 테스트"),
    ("1∼2테스트", "일에서 이 테스트"),
    ("1〜2테스트", "일에서 이 테스트"),
    ("+1.5~2테스트", "플러스 일쩜오에서 이 테스트"),
    ("-1.22~+3.520테스트", "마이너스 일쩜이이에서 플러스 삼쩜오이영 테스트"),
    ("+1,000.50~2,000.75테스트", "플러스 천쩜오영에서 이천쩜칠오 테스트"),
    ("-1,000.50~+2,000.75 범위", "마이너스 천쩜오영에서 플러스 이천쩜칠오 범위"),
    ("1 ~ 2 테스트", "일에서 이 테스트"),
    ("1.2 ~ 3.4구간", "일쩜이에서 삼쩜사 구간"),
    ("1~2.", "일에서 이."),
    ("문장 끝 signed range -1.2~+3.520.", "문장 끝 signed range 마이너스 일쩜이에서 플러스 삼쩜오이영."),
    ("1~2kg은", "일에서 이 킬로그램은"),
    ("+01.5~2", "+01.5~2"),
    ("`+1.5~2테스트`", "`+1.5~2테스트`"),
    ("/path/+1.5~2테스트/log", "/path/+1.5~2테스트/log"),
    ("file1~2.txt", "file1~2.txt"),
]


def main() -> int:
    failures: list[str] = []
    for source, expected in CASES:
        actual = transform(source)
        if actual != expected:
            failures.append(f"{source!r}: expected {expected!r}, got {actual!r}")
    if failures:
        print("\n".join(failures))
        return 1
    print("OK: no tilde numeric range tail spacing failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
