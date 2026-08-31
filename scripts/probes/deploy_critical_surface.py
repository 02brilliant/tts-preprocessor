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
    ProbeCase("malformed_dotted_preserve", "3..140", "3..140"),
    ProbeCase("malformed_dotted_range_preserve", "25..50", "25..50"),
    ProbeCase("file_like_malformed_numeric", "file-25..50.txt", "file-25..50.txt"),
    ProbeCase("code_like_prefix_malformed_numeric", "v25..50", "v25..50"),
    ProbeCase("code_like_token_malformed_numeric", "SKU25..50", "SKU25..50"),
    ProbeCase(
        "dash_like_signed_percent_hyphen_boundary",
        "–2.03%",
        "마이너스 이쩜영삼-퍼센트",
    ),
    ProbeCase(
        "dash_like_range_unit_hyphen_boundary",
        "1–2kg",
        "일에서 이-킬로그램",
    ),
    ProbeCase(
        "numbered_equipment_middle_dot",
        "국토위성 1·2호기",
        "국토위성 일·이호기",
    ),
    ProbeCase(
        "numbered_equipment_middle_dot_sentence",
        "3·4호기를 도입한다",
        "삼·사호기를 도입한다",
    ),
    ProbeCase(
        "managed_numeric_code_version",
        "version-1.5",
        "버전-일쩜오",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy-critical semantic surfaces for canonical probe gates."
    )
    add_runtime_filter_argument(parser)
    parser.add_argument("--binary", type=Path, help="PyInstaller binary path.")
    parser.add_argument("--api", help="API base URL.")
    args = parser.parse_args()

    failed = False
    for runner_name, runner in build_runtime_runners(args):
        results = check_cases(runner_name, runner, CASES)
        for result in results:
            if result.ok:
                continue
            print(format_failure(result), file=sys.stderr)
            failed = True
            break
        if failed:
            break

    if failed:
        return 1

    print(f"[deploy-critical][OK] cases={len(CASES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
