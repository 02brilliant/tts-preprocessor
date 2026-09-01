from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.probes.runtime_matrix import (
    ProbeCase,
    add_runtime_filter_argument,
    build_runtime_runners,
    check_cases,
    format_failure,
)


PROBE_GROUPS: dict[str, tuple[ProbeCase, ...]] = {
    "contextual-decision-contract": (
        ProbeCase("confirmed-decimal-unit", "1.5가지", '일-쩜-오-가지'),
        ProbeCase(
            "confirmed-decimal-occurrence",
            "2.35번 확인했다",
            '이-쩜-삼오-번 확인했다',
        ),
        ProbeCase("specific-owner-precedence", "3.5점", '삼-쩜-오-점'),
    ),
    "gaji": (
        ProbeCase("gaji-native", "4가지", "네-가지"),
        ProbeCase("gaji-native-40", "40가지", "마흔-가지"),
        ProbeCase("gaji-large", "100가지", "백-가지"),
        ProbeCase("gaji-particle", "4가지를", "네-가지를"),
        ProbeCase("gaji-range", "3~4가지", "세-가지에서 네-가지"),
        ProbeCase("gaji-decimal", "1.5가지", '일-쩜-오-가지'),
        ProbeCase("gaji-protected", "`4가지`", "`4가지`"),
    ),
    "quarter-suffix": (
        ProbeCase("quarter-attached-pair", "1분기 2분기", "일분기 이분기"),
        ProbeCase("quarter-year-context", "2025년 1분기", "이천이십오년 일분기"),
        ProbeCase("quarter-decimal", "1.5분기", '일-쩜-오-분기'),
        ProbeCase("quarter-malformed", "1..5분기", "1..5분기"),
        ProbeCase("quarter-range", "1~4분기", "일에서 사-분기"),
        ProbeCase("quarter-protected", "`1분기`", "`1분기`"),
    ),
    "bun-beon-jeom": (
        ProbeCase("bun-time", "5분 뒤", "오분 뒤"),
        ProbeCase("bun-person", "손님 5분이 도착했다", "손님 다섯-분이 도착했다"),
        ProbeCase("bun-remaining", "5분이 남았다", "오분이 남았다"),
        ProbeCase("beon-id", "3번 버스", "삼번 버스"),
        ProbeCase("beon-count", "총 3번 시도했다", "총 세-번 시도했다"),
        ProbeCase("beon-confirm", "3번 확인했다", "세-번 확인했다"),
        ProbeCase("jeom-score", "평점 3점", "평점 삼-점"),
        ProbeCase(
            "jeom-score-anchor-particle",
            "평점은 3점이었다",
            "평점은 삼-점이었다",
        ),
        ProbeCase("jeom-item", "작품 3점을 전시했다", "작품 세-점을 전시했다"),
        ProbeCase("jeom-published-item", "3점이 공개됐다", "세-점이 공개됐다"),
        ProbeCase("jeom-decimal", "3.5점", '삼-쩜-오-점'),
        ProbeCase("bun-decimal-duration", "5.5분 뒤", "오쩜오-분 뒤"),
        ProbeCase("beon-decimal-count", "총 2.35번", '총 이-쩜-삼오-번'),
        ProbeCase("beon-decimal-confirm", "2.35번 확인했다", '이-쩜-삼오-번 확인했다'),
    ),
    "jo-bu": (
        ProbeCase("jo-money", "3조 원", "삼조 원"),
        ProbeCase("jo-group", "학생을 3조로 나눴다", "학생을 세-조로 나눴다"),
        ProbeCase("jo-presentation", "3조가 발표했다", "세-조가 발표했다"),
        ProbeCase("bu-copy", "서류 3부를 제출했다", "서류 세-부를 제출했다"),
        ProbeCase("bu-sequence", "행사 3부가 시작됐다", "행사 삼부가 시작됐다"),
        ProbeCase("bu-defer", "3부가 남았다", "3부가 남았다"),
        ProbeCase(
            "bu-decimal-copy",
            "서류 2.35부를 복사했다",
            '서류 이-쩜-삼오-부를 복사했다',
        ),
    ),
    "dong-ho-address": (
        ProbeCase("dong-address", "3동 502호", "삼-동 오백이-호"),
        ProbeCase("dong-count", "건물 3동을 지었다", "건물 세-동을 지었다"),
        ProbeCase("dong-apartment-id", "아파트 3동", "아파트 삼-동"),
        ProbeCase("ho-id", "3호실", "삼-호실"),
        ProbeCase("ho-count", "피해 농가 3호를 지원했다", "피해 농가 세-호를 지원했다"),
        ProbeCase("ho-defer", "3호가 선정됐다", "3호가 선정됐다"),
    ),
    "pan-dan-deung-cheok": (
        ProbeCase("pan-game", "바둑 3판", "바둑 세-판"),
        ProbeCase("pan-fixed-action", "3판을 겨뤘다", "세-판을 겨뤘다"),
        ProbeCase("pan-edition", "개정 3판", "개정 삼-판"),
        ProbeCase("dan-grade", "태권도 3단", "태권도 삼단"),
        ProbeCase("dan-stack", "상자를 3단으로 쌓았다", "상자를 세-단으로 쌓았다"),
        ProbeCase("dan-shelf", "3단 선반", "세-단 선반"),
        ProbeCase("deung-rank", "대회 3등", "대회 삼등"),
        ProbeCase("deung-light", "조명 3등을 설치했다", "조명 세-등을 설치했다"),
        ProbeCase("cheok-ship", "선박 3척", "선박 세-척"),
        ProbeCase("cheok-length", "길이 3척", "길이 삼-척"),
    ),
    "jang-gwon-pyeon-cheung": (
        ProbeCase("jang-count", "사진 3장", "사진 세-장"),
        ProbeCase("jang-structure", "3장 2절", "삼-장 이절"),
        ProbeCase("jang-defer", "3장이 중요하다", "3장이 중요하다"),
        ProbeCase("gwon-count", "책 3권", "책 세-권"),
        ProbeCase("gwon-structure", "3권 2호", "삼-권 이-호"),
        ProbeCase("gwon-defer", "3권이 남았다", "3권이 남았다"),
        ProbeCase("pyeon-count", "영화 3편", "영화 세-편"),
        ProbeCase("pyeon-structure", "시리즈 3편", "시리즈 삼-편"),
        ProbeCase("pyeon-defer", "3편이 남았다", "3편이 남았다"),
        ProbeCase("cheung-location", "3층 회의실", "삼-층 회의실"),
        ProbeCase("cheung-particle", "3층에서 만났다", "삼-층에서 만났다"),
        ProbeCase("cheung-defer", "3층을 올라갔다", "3층을 올라갔다"),
        ProbeCase("gwon-decimal", "책 2.35권", '책 이-쩜-삼오-권'),
        ProbeCase("pyeon-decimal", "영화 2.35편", '영화 이-쩜-삼오-편'),
        ProbeCase(
            "cheung-decimal",
            "2.35층 회의실",
            '이-쩜-삼오-층 회의실',
        ),
    ),
    "protected-number-unit": (
        ProbeCase("protected-url", "https://example.com/3장", "https://example.com/3장"),
        ProbeCase("protected-path", "/tmp/3권/file", "/tmp/3권/file"),
        ProbeCase("protected-json", '{"value":"3편"}', '{"value":"3편"}'),
        ProbeCase("protected-code", "`3층`", "`3층`"),
        ProbeCase(
            "protected-decimal-json",
            '{"count":"+2.35명"}',
            '{"count":"+2.35명"}',
        ),
    ),
    "mixed-multiple-senses": (
        ProbeCase(
            "observed-deployed-mixed-contextual-decimal",
            "손님 5분이 도착했고 회의는 5분 뒤 시작했다.\u00a0"
            "작품 3점을 전시했고 평점은 3점이었다.\u00a0"
            "학생을 3조로 나눴고 예산은 3조 원이었다. "
            "2.35명쯤, 총 2.34번, 책 2.43권이 있다.",
            '손님 다섯-분이 도착했고 회의는 오분 뒤 시작했다. 작품 세-점을 전시했고 평점은 삼-점이었다. 학생을 세-조로 나눴고 예산은 삼조 원이었다. 이-쩜-삼오-명쯤, 총 이-쩜-삼사-번, 책 이-쩜-사삼-권이 있다.',
        ),
        ProbeCase(
            "mixed-batch4-batch5",
            "행사 3부에 사진 2장과 책 4권을 가져왔다",
            "행사 삼부에 사진 두-장과 책 네-권을 가져왔다",
        ),
        ProbeCase(
            "mixed-floor-work",
            "3층 회의실에서 영화 3편과 시리즈 2편을 봤다",
            "삼-층 회의실에서 영화 세-편과 시리즈 이-편을 봤다",
        ),
    ),
    "malformed-number-unit": (
        ProbeCase("malformed-bun", "01분", "01분"),
        ProbeCase("residual-signed-beon", "+3번", "플러스 삼 번"),
        ProbeCase("residual-signed-jeom", "-3점", "마이너스 삼 점"),
        ProbeCase("malformed-jo", "1,00조", "1,00조"),
        ProbeCase("malformed-bu", "01부", "01부"),
        ProbeCase("residual-signed-dong", "+3동", "플러스 삼 동"),
        ProbeCase("residual-signed-ho", "-3호", "마이너스 삼 호"),
        ProbeCase("residual-decimal-pan", "1.5판", '일-쩜-오-판'),
        ProbeCase("malformed-dan", "1,00단", "1,00단"),
        ProbeCase("malformed-deung", "3A등", "3A등"),
        ProbeCase("malformed-cheok", "01척", "01척"),
        ProbeCase("residual-signed-jang", "+3장", "플러스 삼 장"),
        ProbeCase("residual-signed-gwon", "-3권", "마이너스 삼 권"),
        ProbeCase("residual-decimal-pyeon", "1.5편", '일-쩜-오-편'),
        ProbeCase("malformed-cheung", "01층", "01층"),
    ),
    "dae-multi-sense": (
        ProbeCase("dae-score", "3대2", "삼대이"),
        ProbeCase("dae-machine", "자동차 3대", "자동차 세-대"),
        ProbeCase("dae-generation", "가업을 3대째 이어 왔다", "가업을 삼-대째 이어 왔다"),
        ProbeCase("dae-age", "20대 남성", "이십-대 남성"),
        ProbeCase("dae-major-item", "3대 과제", "삼대 과제"),
        ProbeCase("dae-bare-defer", "3대가 남았다", "3대가 남았다"),
        ProbeCase("dae-decimal-bare", "3.5대", '삼-쩜-오-대'),
        ProbeCase(
            "dae-decimal-machine",
            "차량 +2.35대",
            '차량 플러스 이-쩜-삼오 대',
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe contextual number-unit canonical outputs."
    )
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--api")
    parser.add_argument(
        "--group",
        choices=tuple(PROBE_GROUPS),
        action="append",
        help="Run only selected groups. May be repeated.",
    )
    add_runtime_filter_argument(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = args.group or list(PROBE_GROUPS)
    cases = tuple(case for group in selected for case in PROBE_GROUPS[group])
    failures = []
    for runner_name, runner in build_runtime_runners(args):
        failures.extend(
            result
            for result in check_cases(runner_name, runner, cases, fail_fast=False)
            if not result.ok
        )
    if failures:
        for failure in failures:
            print(format_failure(failure), file=sys.stderr)
        return 1
    print(
        f"[contextual-number-unit][OK] groups={','.join(selected)} "
        f"cases={len(cases)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
