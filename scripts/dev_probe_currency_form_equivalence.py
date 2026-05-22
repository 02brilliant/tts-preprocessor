from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    ("1,000원", "천 원"),
    ("1,000 원", "천 원"),
    ("KRW1000", "천 원"),
    ("KRW1,000", "천 원"),
    ("KRW 1,000", "천 원"),
    ("₩1,000", "천 원"),
    ("￦1,000", "천 원"),
    ("1000KRW", "천 원"),
    ("1,000KRW", "천 원"),
    ("1,000 KRW", "천 원"),
    ("1,000.50원", "천쩜오영 원"),
    ("KRW1,000.50", "천쩜오영 원"),
    ("₩1,000.50", "천쩜오영 원"),
    ("1,000.50KRW", "천쩜오영 원"),
    ("+1,000원", "플러스 천 원"),
    ("KRW+1,000", "플러스 천 원"),
    ("KRW +1,000", "플러스 천 원"),
    ("₩+1,000", "플러스 천 원"),
    ("+₩1,000", "플러스 천 원"),
    ("+1,000KRW", "플러스 천 원"),
    ("-2,500.75원", "마이너스 이천오백쩜칠오 원"),
    ("KRW-2,500.75", "마이너스 이천오백쩜칠오 원"),
    ("₩-2,500.75", "마이너스 이천오백쩜칠오 원"),
    ("-₩2,500.75", "마이너스 이천오백쩜칠오 원"),
    ("-2,500.75KRW", "마이너스 이천오백쩜칠오 원"),
    ("USD1,000", "천 달러"),
    ("$1,000", "천 달러"),
    ("1,000USD", "천 달러"),
    ("1,000달러", "천 달러"),
    ("+01.5원", "+01.5원"),
    ("KRW +01.5", "KRW +01.5"),
    ("₩+01.5", "₩+01.5"),
    ("+01.5KRW", "+01.5KRW"),
    ("1,000  원", "1,000  원"),
    ("KRW  1,000", "KRW  1,000"),
    ("1,000  KRW", "1,000  KRW"),
    ("`KRW1000`", "`KRW1000`"),
    ('{"price":"₩1,000"}', '{"price":"₩1,000"}'),
    ("/path/KRW1000/log", "/path/KRW1000/log"),
    ("SKU-KRW1000", "SKU-KRW1000"),
    ("+1.5 kg", "플러스 일쩜오 킬로그램"),
    ("+25 %", "플러스 이십오 퍼센트"),
    ("+25 ℃", "영상 이십오도"),
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
    print("OK: no currency form equivalence failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
