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
    ProbeCase("protected_backtick", "`3:4테스트`", "`3:4테스트`"),
    ProbeCase("protected_json_value", '{"ratio":"3:4테스트"}', '{"ratio":"3:4테스트"}'),
    ProbeCase("protected_path", "/path/3:4/log", "/path/3:4/log"),
    ProbeCase(
        "protected_url",
        "https://example.com?q=3:4테스트",
        "https://example.com?q=3:4테스트",
    ),
    ProbeCase("protected_line_context", "line 1:23", "line 1:23"),
    ProbeCase("protected_version_context", "version 1:23", "version 1:23"),
    ProbeCase("protected_scripture_context", "요한복음 3:16", "요한복음 3:16"),
    ProbeCase("strong_00_30", "00:30", "영시 삼십분"),
    ProbeCase("strong_01_40", "01:40", "한시 사십분"),
    ProbeCase("strong_09_30", "09:30", "구시 삼십분"),
    ProbeCase("strong_3_04", "3:04", "세시 사분"),
    ProbeCase("strong_13_05", "13:05", "십삼시 오분"),
    ProbeCase("strong_24_09", "24:09", "이십사시 구분"),
    ProbeCase("ambiguous_3_40_preserve", "3:40", "3:40"),
    ProbeCase("ambiguous_13_40_preserve", "13:40", "13:40"),
    ProbeCase("ambiguous_24_50_preserve", "24:50", "24:50"),
    ProbeCase("ambiguous_time_postposition", "3:40에", "세시 사십분에"),
    ProbeCase("ambiguous_time_until", "24:50까지", "이십사시 오십분까지"),
    ProbeCase("ambiguous_ratio_context", "3:40 비율", "삼 대 사십 비율"),
    ProbeCase("ambiguous_score_context", "13:40 스코어", "십삼 대 사십 스코어"),
    ProbeCase("non_time_25_30", "25:30", "이십오 대 삼십"),
    ProbeCase("non_time_3_4", "3:4", "삼 대 사"),
    ProbeCase("non_time_13_5", "13:5", "십삼 대 오"),
    ProbeCase("non_time_1_234", "1:234", "일 대 이백삼십사"),
    ProbeCase("non_time_123_45", "123:45", "백이십삼 대 사십오"),
    ProbeCase("invalid_plus_leading_zero", "+01:2", "+01:2"),
    ProbeCase("invalid_trailing_dot", "+1.:2", "+1.:2"),
    ProbeCase("invalid_missing_integer", "+.5:2", "+.5:2"),
    ProbeCase("invalid_comma_group", "1,00:2", "1,00:2"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate colon/time-like policy across source/runtime paths."
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
    print("OK: no colon/time-like policy failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
