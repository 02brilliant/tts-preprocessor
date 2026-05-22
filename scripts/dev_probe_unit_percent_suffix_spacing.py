from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    ("+1.5kg", "플러스 일쩜오 킬로그램"),
    ("+1.5 kg", "플러스 일쩜오 킬로그램"),
    ("-2.0kg", "마이너스 이쩜영 킬로그램"),
    ("-2.0 kg", "마이너스 이쩜영 킬로그램"),
    ("+1,000.50kg", "플러스 천쩜오영 킬로그램"),
    ("+1,000.50 kg", "플러스 천쩜오영 킬로그램"),
    ("+3.4cm", "플러스 삼쩜사 센티미터"),
    ("+3.4 cm", "플러스 삼쩜사 센티미터"),
    ("+25%", "플러스 이십오 퍼센트"),
    ("+25 %", "플러스 이십오 퍼센트"),
    ("-3.5%", "마이너스 삼쩜오 퍼센트"),
    ("-3.5 %", "마이너스 삼쩜오 퍼센트"),
    ("+1,000.50%", "플러스 천쩜오영 퍼센트"),
    ("+1,000.50 %", "플러스 천쩜오영 퍼센트"),
    ("+1.5  kg", "+1.5  kg"),
    ("+1.5\tkg", "+1.5\tkg"),
    ("+1.5\nkg", "+1.5\nkg"),
    ("+25  %", "+25  %"),
    ("+25\t%", "+25\t%"),
    ("+25\n%", "+25\n%"),
    ("+01.5kg", "+01.5kg"),
    ("+01.5 kg", "+01.5 kg"),
    ("+1,00.5kg", "+1,00.5kg"),
    ("+1,00.5 kg", "+1,00.5 kg"),
    ("+.5kg", "+.5kg"),
    ("+.5 kg", "+.5 kg"),
    ("1.kg", "1.kg"),
    ("1. kg", "1. kg"),
    ("/path/+1.5 kg/log", "/path/+1.5 kg/log"),
    ("/path/+25 %/log", "/path/+25 %/log"),
    ("`+1.5 kg`", "`+1.5 kg`"),
    ('{"unit":"+1.5 kg"}', '{"unit":"+1.5 kg"}'),
    ("+25 ℃", "영상 이십오도"),
    ("1~2 kg", "일에서 이 킬로그램"),
    ("+1:2 테스트", "플러스 일 대 이 테스트"),
    ("+1,000 원", "플러스 천 원"),
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
    print("OK: no unit/percent suffix spacing failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
