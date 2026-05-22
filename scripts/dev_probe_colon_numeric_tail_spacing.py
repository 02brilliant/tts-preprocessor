from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    ("3:4", "삼 대 사"),
    ("+1:2", "플러스 일 대 이"),
    ("13:5", "십삼 대 오"),
    ("1.5:2.0", "일쩜오 대 이쩜영"),
    ("1.50:2", "일쩜오영 대 이"),
    ("1,000:2,000", "천 대 이천"),
    ("+1,000.50:2", "플러스 천쩜오영 대 이"),
    ("3:4테스트", "삼 대 사 테스트"),
    ("+1:2테스트", "플러스 일 대 이 테스트"),
    ("-1:+2범위", "마이너스 일 대 플러스 이 범위"),
    ("1.5:2.0범위", "일쩜오 대 이쩜영 범위"),
    ("1,000:2,000테스트", "천 대 이천 테스트"),
    ("3：4테스트", "삼 대 사 테스트"),
    ("3:4.", "삼 대 사."),
    ("3:4테스트.", "삼 대 사 테스트."),
    ("09:30테스트", "09:30테스트"),
    ("24:09 테스트", "24:09 테스트"),
    ("3:04테스트", "3:04테스트"),
    ("+1:02테스트", "+1:02테스트"),
    ("13:05에 시작", "십삼시 오분에 시작"),
    ("24:09까지", "이십사시 구분까지"),
    ("line 3:4테스트", "line 3:4테스트"),
    ("/path/3:4테스트/log", "/path/3:4테스트/log"),
    ("`3:4테스트`", "`3:4테스트`"),
    ('{"ratio":"3:4테스트"}', '{"ratio":"3:4테스트"}'),
    ("03:4테스트", "03:4테스트"),
    ("+1.:2테스트", "+1.:2테스트"),
    ("+.5:2테스트", "+.5:2테스트"),
    ("1:2:3", "일 대 이 대 삼"),
    ("1:2:3:4:5:6:7:8:9", "1:2:3:4:5:6:7:8:9"),
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
    print("OK: no colon numeric tail spacing failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
