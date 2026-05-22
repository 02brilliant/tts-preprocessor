from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from probe_runtime_matrix import (
    ProbeCase,
    check_cases,
    format_failure,
    run_api_transform,
    run_binary_transform,
    run_production_source_transform,
    run_source_transform,
)


CASE_DATA = [
    ("1만", "일만"),
    ("140만", "백사십만"),
    ("2345만", "이천삼백사십오만"),
    ("2,345만", "이천삼백사십오만"),
    ("2345억", "이천삼백사십오억"),
    ("2,345억", "이천삼백사십오억"),
    ("2345조", "이천삼백사십오조"),
    ("2,345조", "이천삼백사십오조"),
    ("3백4십만", "삼백사십만"),
    ("3백4십억", "삼백사십억"),
    ("3백4십조", "삼백사십조"),
    ("2천8백28억", "이천팔백이십팔억"),
    ("3천4백61억", "삼천사백육십일억"),
    ("1천2백3억", "일천이백삼억"),
    ("4천5백6십7억", "사천오백육십칠억"),
    ("8백28억", "팔백이십팔억"),
    ("28억", "이십팔억"),
    ("1천2백3십4만", "일천이백삼십사만"),
    ("십만", "십만"),
    ("백만", "백만"),
    ("천만", "천만"),
    ("십억", "십억"),
    ("백억", "백억"),
    ("천억", "천억"),
    ("십조", "십조"),
    ("백조", "백조"),
    ("천조", "천조"),
    ("십경", "십경"),
    ("백경", "백경"),
    ("천경", "천경"),
    ("1십만", "일십만"),
    ("2백만", "이백만"),
    ("3천만", "삼천만"),
    ("1십억", "일십억"),
    ("2백억", "이백억"),
    ("3천억", "삼천억"),
    ("1십조", "일십조"),
    ("2백조", "이백조"),
    ("3천조", "삼천조"),
    ("1십경", "일십경"),
    ("2백경", "이백경"),
    ("3천경", "삼천경"),
    ("2백만3천4백", "이백만삼천사백"),
    ("54천만", "오십사천만"),
    ("5억4천만", "오억사천만"),
    ("12만3천4백", "십이만삼천사백"),
    ("1억2천3백만4천5백", "일억이천삼백만사천오백"),
    ("25.50억", "이십오쩜오영 억"),
    ("+25.50억", "플러스 이십오쩜오영 억"),
    ("-25.50억", "마이너스 이십오쩜오영 억"),
    ("1,000.50억", "천쩜오영 억"),
    ("+1,000.50억", "플러스 천쩜오영 억"),
    ("2천8백28.5억", "이천팔백이십팔쩜오 억"),
    ("3천4백61.50억", "삼천사백육십일쩜오영 억"),
    ("2천8백28억 원", "이천팔백이십팔억 원"),
    ("2,345억 원", "이천삼백사십오억 원"),
    ("25.50억 원", "이십오쩜오영 억 원"),
    ("12만3천4백 원", "십이만삼천사백 원"),
    ("5억4천만 원", "오억사천만 원"),
    ("2천8백28억테스트", "이천팔백이십팔억 테스트"),
    ("2,345억테스트", "이천삼백사십오억 테스트"),
    ("25.50억테스트", "이십오쩜오영 억 테스트"),
    ("3백4십만테스트", "삼백사십만 테스트"),
    ("5억4천만테스트", "오억사천만 테스트"),
    ("12만3천4백테스트", "십이만삼천사백 테스트"),
    ("2천8백28억abc", "이천팔백이십팔억abc"),
    ("2,345억abc", "이천삼백사십오억abc"),
    ("25.50억abc", "이십오쩜오영 억abc"),
    ("3백4십만abc", "삼백사십만abc"),
    ("5억4천만abc", "오억사천만abc"),
    ("12만3천4백abc", "십이만삼천사백abc"),
    ("2천8백28억,", "이천팔백이십팔억,"),
    ("2345억,", "이천삼백사십오억,"),
    ("2,345억,", "이천삼백사십오억,"),
    ("1만,", "일만,"),
    ("140만,", "백사십만,"),
    ("3백4십만,", "삼백사십만,"),
    ("5억4천만,", "오억사천만,"),
    ("12만3천4백,", "십이만삼천사백,"),
    ("25.50억,", "이십오쩜오영 억,"),
    ("2천8백28억.", "이천팔백이십팔억."),
    ("2천8백28억!", "이천팔백이십팔억!"),
    ("2천8백28억?", "이천팔백이십팔억?"),
    ("2천8백28억)", "이천팔백이십팔억)"),
    (
        "2345억, 2,345억, 1만, 140만, 3백4십만, 5억4천만, 12만3천4백, 2백만3천4백, 54천만, 1억2천3백만4천5백, 25.50억, 2천8백28억테스트, 2천8백28억abc",
        "이천삼백사십오억, 이천삼백사십오억, 일만, 백사십만, 삼백사십만, 오억사천만, 십이만삼천사백, 이백만삼천사백, 오십사천만, 일억이천삼백만사천오백, 이십오쩜오영 억, 이천팔백이십팔억 테스트, 이천팔백이십팔억abc",
    ),
    ("v2천8백28억", "v2천8백28억"),
    ("SKU2천8백28억", "SKU2천8백28억"),
    ("abc2,345억", "abc2,345억"),
    ("v3백4십만", "v3백4십만"),
    ("SKU3백4십만", "SKU3백4십만"),
    ("abc3백4십만", "abc3백4십만"),
    ("v5억4천만", "v5억4천만"),
    ("SKU12만3천4백", "SKU12만3천4백"),
    ("2,34억", "2,34억"),
    ("2,,345억", "2,,345억"),
    ("+.5억", "+.5억"),
    ("1.억", "1.억"),
    ("25..50억", "25..50억"),
    ("2천8백..28억", "2천8백..28억"),
    ("2천8백28..5억", "2천8백28..5억"),
    ("2천8백.28억", "2천8백.28억"),
    ("3백..4십만", "3백..4십만"),
    ("3백4십..만", "3백4십..만"),
    ("3십백만", "3십백만"),
    ("3만만", "3만만"),
    ("1억억", "1억억"),
    ("1천2억", "1천2억"),
    ("1백2천", "1백2천"),
    ("`2천8백28억`", "`2천8백28억`"),
    ("`2,345억`", "`2,345억`"),
    ("`25.50억`", "`25.50억`"),
    ("`3백4십만`", "`3백4십만`"),
    ("`5억4천만`", "`5억4천만`"),
    ("`12만3천4백`", "`12만3천4백`"),
    ('{"amount":"3천4백61억 원"}', '{"amount":"3천4백61억 원"}'),
    ('{"amount":"2,345억"}', '{"amount":"2,345억"}'),
    ('{"amount":"25.50억"}', '{"amount":"25.50억"}'),
    ("/path/2천8백28억/log", "/path/2천8백28억/log"),
    ("/path/2,345억/log", "/path/2,345억/log"),
    ("/path/3백4십만/log", "/path/3백4십만/log"),
    ("/path/5억4천만/log", "/path/5억4천만/log"),
    ("https://example.com?q=2천8백28억", "https://example.com?q=2천8백28억"),
    ("https://example.com?q=2,345억", "https://example.com?q=2,345억"),
    ("https://example.com?q=3백4십만", "https://example.com?q=3백4십만"),
]

SOURCE_ONLY_REGRESSION_DATA = [
    ("2,345", "이천삼백사십오"),
    ("25.50", "이십오쩜오영"),
    ("+1.5 kg", "플러스 일쩜오 킬로그램"),
    ("+25 %", "플러스 이십오 퍼센트"),
    ("KRW1000", "천 원"),
    ("+25℃", "영상 이십오도"),
    ("1~2테스트", "일에서 이 테스트"),
    ("3:4테스트", "삼 대 사 테스트"),
    ("1-2kg", "일에서 이 킬로그램"),
    ("1-2테스트", "1-2테스트"),
    ("09:30", "구시 삼십분"),
]


CASES = [
    ProbeCase(f"large_unit_{index:03d}", text, expected)
    for index, (text, expected) in enumerate(CASE_DATA, start=1)
]

SOURCE_ONLY_REGRESSION_CASES = [
    ProbeCase(f"regression_{index:03d}", text, expected)
    for index, (text, expected) in enumerate(SOURCE_ONLY_REGRESSION_DATA, start=1)
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate large-unit numeric surfaces across source/runtime paths."
    )
    parser.add_argument(
        "--binary",
        type=Path,
        help="Optional PyInstaller binary path to validate with --rollout-mode span_default.",
    )
    parser.add_argument(
        "--api",
        help="Optional API base URL, for example http://10.20.10.162:8010.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_cases = [*CASES, *SOURCE_ONLY_REGRESSION_CASES]
    runners = [
        ("source", run_source_transform),
        ("production_source", run_production_source_transform),
    ]

    if args.binary is not None:
        binary_path = args.binary.expanduser()
        runners.append(("binary", lambda text: run_binary_transform(binary_path, text)))

    if args.api:
        runners.append(("api", lambda text: run_api_transform(args.api, text)))

    for runner_name, runner in runners:
        results = check_cases(runner_name, runner, all_cases)
        failure = next((result for result in results if not result.ok), None)
        if failure is not None:
            print(format_failure(failure))
            return 1
    print("OK: no large-unit numeric surface coverage failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
