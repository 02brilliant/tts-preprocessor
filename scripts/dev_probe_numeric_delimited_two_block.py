from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.span_engine.transform import transform


HYPHEN_STANDALONE = ["1-2", "1–2", "03-04", "12-31", "123-456"]
HYPHEN_RANGE_UNITS = [
    ("1-2장", "일에서 이 장"),
    ("1–2장", "일에서 이 장"),
    ("1~2장", "일에서 이 장"),
    ("1～2장", "일에서 이 장"),
    ("3-4페이지", "삼에서 사 페이지"),
    ("10-20개", "십에서 이십 개"),
    ("10–20개", "십에서 이십 개"),
    ("2-3명", "이에서 삼 명"),
    ("3-5분", "삼에서 오 분"),
    ("1-2kg", "일에서 이 킬로그램"),
    ("1.5-2kg", "일쩜오에서 이 킬로그램"),
    ("1–2kg", "일에서 이 킬로그램"),
    ("1.5–2kg", "일쩜오에서 이 킬로그램"),
    ("1~2kg", "일에서 이 킬로그램"),
    ("1.5~2kg", "일쩜오에서 이 킬로그램"),
    ("1～2kg", "일에서 이 킬로그램"),
    ("1.5～2kg", "일쩜오에서 이 킬로그램"),
    ("2-3cm", "이에서 삼 센티미터"),
    ("10-20%", "십에서 이십 퍼센트"),
    ("100-200원", "백에서 이백 원"),
    ("5-3개", "오에서 삼 개"),
]
HYPHEN_PRESERVE = [
    "1-2테스트",
    "1–2테스트",
    "1~2테스트",
    "1～2테스트",
    "1-2버그",
    "1-2alpha",
    "1.5-2alpha",
    "1-2mph",
    "v1-2",
    "v1.5-2",
    "/path/1-2/log",
    "/path/1–2/log",
    "`1-2`",
    "`1.5-2kg`",
    "`1~2개`",
]
HYPHEN_NO_RANGE = ["1-2케이스ID"]

COLON_STANDALONE = ["13:05", "13：05", "9:30", "1:2", "1：2", "3:15", "10:20"]
COLON_TIME = [
    ("13:05에 시작", "십삼시 오분에 시작"),
    ("13：05에 시작", "십삼시 오분에 시작"),
    ("14:00부터", "십사시부터"),
    ("18:30까지", "십팔시 삼십분까지"),
    ("오전 9:30", "오전 아홉시 삼십분"),
    ("오후 3:15", "오후 세시 십오분"),
    ("회의 14:00", "회의 십사시"),
    ("마감 18:00", "마감 십팔시"),
]
COLON_SEMANTIC_PAIR = [
    ("2:0으로 이겼다", "이 대 영으로 이겼다"),
    ("3:1 승리", "삼 대 일 승리"),
    ("1:2 비율", "일 대 이 비율"),
    ("1.5:2 비율", "일쩜오 대 이 비율"),
    ("1：2 비율", "일 대 이 비율"),
    ("16:9 화면비", "십육 대 구 화면비"),
]
COLON_PRESERVE = [
    "요한복음 3:16",
    "요한복음 3：16",
    "line 10:20",
    "영상 1:23",
    "영상 1：23",
    "재생시간 03:15",
    "타임라인 00:03",
    "13:99",
    "13:99에 시작",
    "24:01부터",
]

NEIGHBORS = [("25℃", "이십오도"), ("pH 7.4", "피에이치 칠쩜사"), ("3kg", "삼 킬로그램")]


def _failures_for_exact_preserve(cases: list[str]) -> list[str]:
    failures: list[str] = []
    for source in cases:
        out = transform(source)
        if out != source:
            failures.append(f"expected preserve: {source!r}\nOUT={out}")
    return failures


def _failures_for_transform(cases: list[tuple[str, str]]) -> list[str]:
    failures: list[str] = []
    for source, expected in cases:
        out = transform(source)
        if out != expected:
            failures.append(f"expected transform: {source!r}\nEXPECTED={expected}\nOUT={out}")
    return failures


def _failures_for_neighbor_survival() -> list[str]:
    failures: list[str] = []
    preserve_cases = HYPHEN_PRESERVE + COLON_PRESERVE
    transform_cases = HYPHEN_RANGE_UNITS + COLON_TIME + COLON_SEMANTIC_PAIR
    for protected in preserve_cases:
        for neighbor, expected_neighbor in NEIGHBORS:
            text = f"검증 문장입니다. {protected}는 그대로 두고 {neighbor}는 처리해야 합니다."
            out = transform(text)
            if out == text or protected not in out or expected_neighbor not in out:
                failures.append(
                    f"neighbor failed for preserve={protected!r}, neighbor={neighbor!r}\nOUT={out}"
                )
    for surface, expected_surface in transform_cases:
        for neighbor, expected_neighbor in NEIGHBORS:
            text = f"검증 문장입니다. {surface}. 그리고 {neighbor}는 처리해야 합니다."
            out = transform(text)
            if out == text or expected_surface not in out or expected_neighbor not in out:
                failures.append(
                    f"neighbor failed for surface={surface!r}, neighbor={neighbor!r}\nOUT={out}"
                )
    return failures


def _failures_for_no_range_claim(cases: list[str]) -> list[str]:
    failures: list[str] = []
    for source in cases:
        out = transform(source)
        if "일에서 이 케이스" in out or "1-2케이스" not in out:
            failures.append(f"expected no range claim: {source!r}\nOUT={out}")
    return failures


def main() -> None:
    failures: list[str] = []
    failures.extend(_failures_for_exact_preserve(HYPHEN_STANDALONE))
    failures.extend(_failures_for_exact_preserve(HYPHEN_PRESERVE))
    failures.extend(_failures_for_no_range_claim(HYPHEN_NO_RANGE))
    failures.extend(_failures_for_transform(HYPHEN_RANGE_UNITS))
    failures.extend(_failures_for_exact_preserve(COLON_STANDALONE))
    failures.extend(_failures_for_exact_preserve(COLON_PRESERVE))
    failures.extend(_failures_for_transform(COLON_TIME))
    failures.extend(_failures_for_transform(COLON_SEMANTIC_PAIR))
    failures.extend(_failures_for_neighbor_survival())
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, failure in enumerate(failures[:100], 1):
            print("=" * 80)
            print("FAIL", index)
            print(failure)
        raise SystemExit(1)
    print("OK: no numeric-delimited two-block failures")


if __name__ == "__main__":
    main()
