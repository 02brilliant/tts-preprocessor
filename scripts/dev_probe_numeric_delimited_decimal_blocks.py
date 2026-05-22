from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


CASES = [
    ("1.5:2 비율", "일쩜오 대 이 비율"),
    ("1.5:2.0 비율", "일쩜오 대 이쩜영 비율"),
    ("0.5:1 희석", "영쩜오 대 일 희석"),
    ("1.25:100 축척", "일쩜이오 대 백 축척"),
    ("1,000.5:2 비율", "천쩜오 대 이 비율"),
    ("1:1,000,000.000 축척", "일 대 백만쩜영영영 축척"),
    ("2.0:0.0 무승부", "이쩜영 대 영쩜영 무승부"),
    ("3.50:1.25 경기", "삼쩜오영 대 일쩜이오 경기"),
    ("1.5:2", "1.5:2"),
    ("1.5:2 영상", "1.5:2 영상"),
    ("01.5:2 비율", "01.5:2 비율"),
    ("1.:2 비율", "1.:2 비율"),
    (".5:2 비율", ".5:2 비율"),
    ("1,00.5:2 비율", "1,00.5:2 비율"),
    ("-1.5:2 비율", "마이너스 일쩜오 대 이 비율"),
    ("+1.5:2 비율", "플러스 일쩜오 대 이 비율"),
    ("1.5-2kg", "일쩜오에서 이 킬로그램"),
    ("0.5-1.0cm", "영쩜오에서 일쩜영 센티미터"),
    ("1,000.5-2,000.75원", "천쩜오에서 이천쩜칠오 원"),
    ("2.0-1.5kg", "이쩜영에서 일쩜오 킬로그램"),
    ("1.50-2.00kg", "일쩜오영에서 이쩜영영 킬로그램"),
    ("0.05-0.10cm", "영쩜영오에서 영쩜일영 센티미터"),
    ("1.25~2.5kg", "일쩜이오에서 이쩜오 킬로그램"),
    ("1.25–2.5kg", "일쩜이오에서 이쩜오 킬로그램"),
    ("1.25～2.5kg", "일쩜이오에서 이쩜오 킬로그램"),
    ("1.5-2", "1.5-2"),
    ("1.5-2테스트", "1.5-2테스트"),
    ("v1.5-2", "v1.5-2"),
    ("/path/1.5-2kg/log", "/path/1.5-2kg/log"),
    ("`1.5-2kg`", "`1.5-2kg`"),
    ("01.5-2kg", "01.5-2kg"),
    ("1.-2kg", "1.-2kg"),
    (".5-2kg", ".5-2kg"),
    ("1,00.5-2kg", "1,00.5-2kg"),
    ("-1.5-2kg", "-1.5-2kg"),
    ("pH 7.4와 1.5-2kg", "피에이치 칠쩜사와 일쩜오에서 이 킬로그램"),
]


def main() -> None:
    failures: list[str] = []
    for source, expected in CASES:
        out = transform(source)
        if out != expected:
            failures.append(f"{source!r}\nEXPECTED={expected}\nOUT={out}")
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, failure in enumerate(failures[:100], 1):
            print("=" * 80)
            print("FAIL", index)
            print(failure)
        raise SystemExit(1)
    print("OK: no numeric-delimited decimal block failures")


if __name__ == "__main__":
    main()
