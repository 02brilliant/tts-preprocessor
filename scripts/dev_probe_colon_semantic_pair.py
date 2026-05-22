from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


SEMANTIC_PAIR_POSITIVE = [
    ("1:2 비율", "일 대 이 비율"),
    ("1.5:2 비율", "일쩜오 대 이 비율"),
    ("1.5:2.0 비율", "일쩜오 대 이쩜영 비율"),
    ("비율 1:2", "비율 일 대 이"),
    ("16:9 화면비", "십육 대 구 화면비"),
    ("1:100 희석", "일 대 백 희석"),
    ("1:500 축척", "일 대 오백 축척"),
    ("1:1,000,000 축척", "일 대 백만 축척"),
    ("2:0으로 이겼다", "이 대 영으로 이겼다"),
    ("3:1 승리", "삼 대 일 승리"),
    ("0:0 무승부", "영 대 영 무승부"),
    ("3:0 완승", "삼 대 영 완승"),
    ("5:2 압승", "오 대 이 압승"),
    ("2:1 역전승", "이 대 일 역전승"),
    ("2:1 경기", "이 대 일 경기"),
    ("경기 2:1", "경기 이 대 일"),
    ("3:2 세트", "삼 대 이 세트"),
    ("매치 2:0", "매치 이 대 영"),
    ("게임 1:0", "게임 일 대 영"),
    ("전적 4:3", "전적 사 대 삼"),
    ("배율 1:2", "배율 일 대 이"),
    ("1:2 스케일", "일 대 이 스케일"),
    ("1,000:2,000 비율", "천 대 이천 비율"),
    ("1,000.5:2 비율", "천쩜오 대 이 비율"),
    ("1：2 비율", "일 대 이 비율"),
    ("1.5：2 비율", "일쩜오 대 이 비율"),
    ("2：0으로 이겼다", "이 대 영으로 이겼다"),
    ("-1:2 비율", "마이너스 일 대 이 비율"),
    ("-1.5:2 비율", "마이너스 일쩜오 대 이 비율"),
    ("+1:2 비율", "플러스 일 대 이 비율"),
    ("+1.5:2 비율", "플러스 일쩜오 대 이 비율"),
    ("1:2", "일 대 이"),
    ("1.5:2", "일쩜오 대 이"),
    ("1.5:2 영상", "일쩜오 대 이 영상"),
    ("1:1,000,000", "일 대 백만"),
    ("2:0으로 끝났다", "이 대 영으로 끝났다"),
    ("3:1로 마무리", "삼 대 일로 마무리"),
    ("1:2로 섞었다", "일 대 이로 섞었다"),
    ("3:4테스트", "삼 대 사 테스트"),
    ("+1:2테스트", "플러스 일 대 이 테스트"),
    ("1.5:2.0범위", "일쩜오 대 이쩜영 범위"),
    ("1,000:2,000테스트", "천 대 이천 테스트"),
]

SEMANTIC_PAIR_PRESERVE = [
    "01:2 비율",
    "1:02 비율",
    "01,000:2 비율",
    "1:10,00 비율",
    "100,000,000:1 축척",
    "01.5:2 비율",
    "1.:2 비율",
    ".5:2 비율",
    "3:16",
    "10:20",
    "13：05",
    "요한복음 3:16",
    "요한복음 3：16",
    "창세기 1:05",
    "문서 3:16",
    "참조 10:20",
    "영상 1:23",
    "영상 1：23",
    "재생시간 03:15",
    "타임라인 10:20",
    "line 10:20",
    "case 3:16",
    "/path/1:2/log",
    '{"ratio":"1:2"}',
]

TIME_POSITIVE = [
    ("13:05에 시작", "십삼시 오분에 시작"),
    ("13：05에 시작", "십삼시 오분에 시작"),
    ("14:00부터", "십사시부터"),
    ("18:30까지", "십팔시 삼십분까지"),
    ("오전 9:30", "오전 아홉시 삼십분"),
    ("회의 14:00", "회의 십사시"),
    ("2:00에 시작", "두시에 시작"),
]

NEIGHBORS = [
    ("25℃", "이십오도"),
    ("$25.99", "이십오쩜구구 달러"),
    ("3kg", "삼 킬로그램"),
]


def _failures_for_transform(cases: list[tuple[str, str]]) -> list[str]:
    failures: list[str] = []
    for source, expected in cases:
        out = transform(source)
        if out != expected:
            failures.append(
                f"expected transform: {source!r}\nEXPECTED={expected}\nOUT={out}"
            )
    return failures


def _failures_for_preserve(cases: list[str]) -> list[str]:
    failures: list[str] = []
    for source in cases:
        out = transform(source)
        if out != source:
            failures.append(f"expected preserve: {source!r}\nOUT={out}")
    return failures


def _failures_for_neighbor_survival() -> list[str]:
    failures: list[str] = []
    for surface, expected_surface in SEMANTIC_PAIR_POSITIVE:
        for neighbor, expected_neighbor in NEIGHBORS:
            text = f"검증 문장입니다. {surface}과 {neighbor}도 처리해야 합니다."
            out = transform(text)
            if out == text or expected_surface not in out or expected_neighbor not in out:
                failures.append(
                    f"neighbor failed for surface={surface!r}, neighbor={neighbor!r}\nOUT={out}"
                )
    for preserve in SEMANTIC_PAIR_PRESERVE:
        for neighbor, expected_neighbor in NEIGHBORS:
            text = f"검증 문장입니다. {preserve}는 그대로 두고 {neighbor}는 처리해야 합니다."
            out = transform(text)
            if out == text or preserve not in out or expected_neighbor not in out:
                failures.append(
                    f"neighbor failed for preserve={preserve!r}, neighbor={neighbor!r}\nOUT={out}"
                )
    return failures


def main() -> None:
    failures: list[str] = []
    failures.extend(_failures_for_transform(SEMANTIC_PAIR_POSITIVE))
    failures.extend(_failures_for_preserve(SEMANTIC_PAIR_PRESERVE))
    failures.extend(_failures_for_transform(TIME_POSITIVE))
    failures.extend(_failures_for_neighbor_survival())
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, failure in enumerate(failures[:100], 1):
            print("=" * 80)
            print("FAIL", index)
            print(failure)
        raise SystemExit(1)
    print("OK: no colon semantic pair failures")


if __name__ == "__main__":
    main()
