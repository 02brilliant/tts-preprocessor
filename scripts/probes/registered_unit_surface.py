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


CASES = [
    ProbeCase(
        "cjk_kiloliter_tax_sentence",
        "생맥주 주세는 1㎘당 17만7200원 오른다.",
        "생맥주 주세는 일 킬로리터당 십칠만칠천이백 원 오른다.",
    ),
    ProbeCase(
        "korean_large_unit_square_meter",
        "연면적 1만㎡ 규모로 조성된다.",
        "연면적 일만 제곱미터 규모로 조성된다.",
    ),
    ProbeCase(
        "hangul_context_kilometer",
        "수 km을 달려왔다.",
        "수 킬로미터를 달려왔다.",
    ),
    ProbeCase(
        "cheung_underground_and_above_ground",
        "지하 1층부터 지상 3층까지.",
        "지하 일 층부터 지상 삼 층까지.",
    ),
    ProbeCase(
        "decimal_large_unit_kilogram",
        "3.5만kg",
        "삼쩜오 만 킬로그램",
    ),
    ProbeCase(
        "shared_large_unit_kilogram_range",
        "45~50만kg이다.",
        "사십오에서 오십만 킬로그램이다.",
    ),
    ProbeCase("ascii_microliter_alias", "55µL", "오십오 마이크로리터"),
    ProbeCase("cjk_microliter", "55㎕", "오십오 마이크로리터"),
    ProbeCase("ascii_deciliter_alias", "55dL", "오십오 데시리터"),
    ProbeCase("cjk_deciliter", "55㎗", "오십오 데시리터"),
    ProbeCase("ascii_kiloliter_alias", "55kL", "오십오 킬로리터"),
    ProbeCase("cjk_kiloliter_unsafe_tail", "55㎘abc", "55㎘abc"),
    ProbeCase("cjk_microliter_unsafe_tail", "55㎕abc", "55㎕abc"),
    ProbeCase("cjk_deciliter_unsafe_tail", "55㎗abc", "55㎗abc"),
    ProbeCase("uppercase_kl_is_not_a_unit", "1KL", "1KL"),
    ProbeCase("uppercase_dl_is_not_a_unit", "1DL", "1DL"),
    ProbeCase("ascii_nanometer", "55nm", "오십오 나노미터"),
    ProbeCase("cjk_micrometer", "55㎛", "오십오 마이크로미터"),
    ProbeCase("ascii_pascal", "55Pa", "오십오 파스칼"),
    ProbeCase("cjk_kilovolt", "55㎸", "오십오 킬로볼트"),
    ProbeCase("hectopascal_weather", "1013hPa", "천십삼 헥토파스칼"),
    ProbeCase("gigawatt", "55GW", "오십오 기가와트"),
    ProbeCase("terahertz", "55THz", "오십오 테라헤르츠"),
    ProbeCase("kilobit_per_second", "55Kbps", "오십오 킬로비피에스"),
    ProbeCase("uppercase_kw_is_not_a_unit", "1KW", "1KW"),
    ProbeCase("femtometer_symbol_preserves", "55㎙", "55㎙"),
    ProbeCase("ascii_second_alias", "55sec", "오십오 초"),
    ProbeCase("ascii_millisecond", "55ms", "오십오 밀리초"),
    ProbeCase("ascii_basis_point", "55bp", "오십오 베이시스 포인트"),
    ProbeCase("uppercase_basis_point", "55BP", "오십오 베이시스 포인트"),
    ProbeCase("ascii_bit_per_second", "55bps", "오십오 비피에스"),
    ProbeCase("ascii_spaced_bit_per_second", "55 bps", "오십오 비피에스"),
    ProbeCase("ascii_spaced_megabit_per_second", "10 Mbps", "십 메가비피에스"),
    ProbeCase("prefixed_je_bit_per_second", "제10bps", "제십 비피에스"),
    ProbeCase("ascii_microsecond", "55µs", "오십오 마이크로초"),
    ProbeCase("cjk_millisecond", "55㎳", "오십오 밀리초"),
    ProbeCase("bare_s_is_not_a_unit", "5s", "5s"),
    ProbeCase("uppercase_ms_is_not_a_unit", "5MS", "5MS"),
    ProbeCase("compound_meter_per_sec_unchanged", "5m/sec", "초속 오 미터"),
    ProbeCase(
        "registered_unit_production_sentence",
        (
            "생맥주 주세는 1㎘당 17만7200원 오른다. "
            "연면적 1만㎡ 규모로 조성된다. "
            "수 km을 달려왔다. "
            "지하 1층부터 지상 3층까지. "
            "3.5만kg, 45~50만kg이다."
        ),
        (
            "생맥주 주세는 일 킬로리터당 십칠만칠천이백 원 오른다. "
            "연면적 일만 제곱미터 규모로 조성된다. "
            "수 킬로미터를 달려왔다. "
            "지하 일 층부터 지상 삼 층까지. "
            "삼쩜오 만 킬로그램, 사십오에서 오십만 킬로그램이다."
        ),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate registered unit surfaces that a committed-HEAD binary "
            "would leave literal."
        )
    )
    parser.add_argument(
        "--binary",
        type=Path,
        help="Optional PyInstaller binary path to validate with the production command.",
    )
    parser.add_argument(
        "--api",
        help="Optional API base URL, for example http://10.20.10.162:8010.",
    )
    add_runtime_filter_argument(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        runners = build_runtime_runners(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    for runner_name, runner in runners:
        results = check_cases(runner_name, runner, CASES)
        failure = next((result for result in results if not result.ok), None)
        if failure is not None:
            print(format_failure(failure))
            return 1
    print("OK: no registered unit surface failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
