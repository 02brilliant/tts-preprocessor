from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.probe_runtime_matrix import (
    ProbeCase,
    check_cases,
    format_failure,
    run_api_transform,
    run_binary_transform,
    run_production_source_transform,
    run_source_transform,
)


CASES = [
    ProbeCase("unit", '{"unit":"+1.5 kg"}', '{"unit":"+1.5 kg"}'),
    ProbeCase("percent", '{"percent":"+25 %"}', '{"percent":"+25 %"}'),
    ProbeCase("krw_code", '{"price":"KRW1000"}', '{"price":"KRW1000"}'),
    ProbeCase("krw_suffix", '{"price":"1,000원"}', '{"price":"1,000원"}'),
    ProbeCase("usd_spaced", '{"price":"USD 1,000"}', '{"price":"USD 1,000"}'),
    ProbeCase("temperature", '{"temp":"+25℃"}', '{"temp":"+25℃"}'),
    ProbeCase("tilde_range", '{"range":"1~2테스트"}', '{"range":"1~2테스트"}'),
    ProbeCase("colon_tail", '{"ratio":"3:4테스트"}', '{"ratio":"3:4테스트"}'),
    ProbeCase("large_unit_mixed", '{"large":"2천8백28억"}', '{"large":"2천8백28억"}'),
    ProbeCase("large_unit_comma", '{"large":"2,345억"}', '{"large":"2,345억"}'),
    ProbeCase("hyphen_unit", '{"hyphen":"1-2kg"}', '{"hyphen":"1-2kg"}'),
    ProbeCase(
        "outside_json_transforms",
        '{"price":"KRW1000"} 밖의 KRW1000',
        '{"price":"KRW1000"} 밖의 천 원',
    ),
    ProbeCase(
        "integrated_sentence",
        (
            "보호 구간에는 `KRW1000`, `2천8백28억`, "
            '{"price":"1,000원"}, {"range":"1~2테스트"}, '
            "/path/2,345억/log, https://example.com?q=KRW1000이 있고, "
            "문장 밖의 KRW1000, 2천8백28억, 1~2테스트는 처리되어야 한다."
        ),
        (
            "보호 구간에는 `KRW1000`, `2천8백28억`, "
            '{"price":"1,000원"}, {"range":"1~2테스트"}, '
            "/path/2,345억/log, https://example.com?q=KRW1000이 있고, "
            "문장 밖의 천 원, 이천팔백이십팔억, 일에서 이 테스트는 처리되어야 한다."
        ),
    ),
    ProbeCase(
        "non_json_quote_policy_unchanged",
        '그는 "KRW1000"이라고 말했다.',
        '그는 "천 원"이라고 말했다.',
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate JSON-like protected spans across source/runtime paths."
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
        results = check_cases(runner_name, runner, CASES)
        failure = next((result for result in results if not result.ok), None)
        if failure is not None:
            print(format_failure(failure))
            return 1
    print("OK: no JSON-like protected span failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
