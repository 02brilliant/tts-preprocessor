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
    ProbeCase("standalone_zero_fraction", "0.050", "영쩜영오영"),
    ProbeCase("standalone_trailing_zero", "1.50", "일쩜오영"),
    ProbeCase("standalone_all_zero_fraction", "25.00", "이십오쩜영영"),
    ProbeCase("signed_plus_zero_fraction", "+0.050", "플러스 영쩜영오영"),
    ProbeCase("signed_minus_zero_fraction", "-0.050", "마이너스 영쩜영오영"),
    ProbeCase("signed_plus_trailing_zero", "+25.50", "플러스 이십오쩜오영"),
    ProbeCase("signed_minus_trailing_zero", "-25.50", "마이너스 이십오쩜오영"),
    ProbeCase("standalone_comma_decimal", "1,000.50", "천쩜오영"),
    ProbeCase("unit_attached", "+1.50kg", "플러스 일쩜오영 킬로그램"),
    ProbeCase("unit_spaced", "+1.50 kg", "플러스 일쩜오영 킬로그램"),
    ProbeCase("unit_minus_all_zero_fraction", "-2.00kg", "마이너스 이쩜영영 킬로그램"),
    ProbeCase("unit_zero_fraction", "0.050cm", "영쩜영오영 센티미터"),
    ProbeCase("percent_attached", "+25.50%", "플러스 이십오쩜오영 퍼센트"),
    ProbeCase("percent_spaced", "+25.50 %", "플러스 이십오쩜오영 퍼센트"),
    ProbeCase("percent_zero_fraction", "0.050%", "영쩜영오영 퍼센트"),
    ProbeCase("percent_comma_decimal", "+1,000.50%", "플러스 천쩜오영 퍼센트"),
    ProbeCase("krw_suffix", "1,000.50원", "천쩜오영 원"),
    ProbeCase("krw_signed_suffix", "+1,000.50원", "플러스 천쩜오영 원"),
    ProbeCase("krw_code_signed_prefix", "KRW+1,000.50", "플러스 천쩜오영 원"),
    ProbeCase("krw_symbol_signed_prefix", "₩+1,000.50", "플러스 천쩜오영 원"),
    ProbeCase("usd_code_attached", "USD1,000.50", "천쩜오영 달러"),
    ProbeCase("usd_code_spaced", "USD 1,000.50", "천쩜오영 달러"),
    ProbeCase("usd_symbol", "$1,000.50", "천쩜오영 달러"),
    ProbeCase("usd_suffix_spaced", "1,000.50 USD", "천쩜오영 달러"),
    ProbeCase("eur_code", "EUR1,000.50", "천쩜오영 유로"),
    ProbeCase("eur_symbol", "€1,000.50", "천쩜오영 유로"),
    ProbeCase("jpy_code", "JPY1,000.50", "천쩜오영 엔"),
    ProbeCase("jpy_symbol", "¥1,000.50", "천쩜오영 엔"),
    ProbeCase("gbp_code", "GBP1,000.50", "천쩜오영 파운드"),
    ProbeCase("gbp_symbol", "£1,000.50", "천쩜오영 파운드"),
    ProbeCase("usd_all_zero_fraction", "USD1.00", "일쩜영영 달러"),
    ProbeCase("usd_zero_fraction", "USD0.050", "영쩜영오영 달러"),
    ProbeCase("fahrenheit_attached", "+77.50°F", "화씨 영상 칠십칠쩜오영도"),
    ProbeCase("fahrenheit_spaced", "+77.50 °F", "화씨 영상 칠십칠쩜오영도"),
    ProbeCase("celsius_minus_attached", "-0.050℃", "영하 영쩜영오영도"),
    ProbeCase("celsius_minus_spaced", "-0.050 ℃", "영하 영쩜영오영도"),
    ProbeCase("celsius_plus_all_zero_fraction", "+1.00℃", "영상 일쩜영영도"),
    ProbeCase("large_unit_decimal", "25.50억", "이십오쩜오영 억"),
    ProbeCase("large_unit_plus", "+25.50억", "플러스 이십오쩜오영 억"),
    ProbeCase("large_unit_minus", "-25.50억", "마이너스 이십오쩜오영 억"),
    ProbeCase("large_unit_zero_fraction", "0.050억", "영쩜영오영 억"),
    ProbeCase("large_unit_comma_decimal", "1,000.50억", "천쩜오영 억"),
    ProbeCase(
        "large_unit_mixed_decimal",
        "2천8백28.50억",
        "이천팔백이십팔쩜오영 억",
    ),
    ProbeCase("large_unit_currency_tail", "25.50억 원", "이십오쩜오영 억 원"),
    ProbeCase("tilde_decimal", "1.50~2.0", "일쩜오영에서 이쩜영"),
    ProbeCase("tilde_zero_fraction", "0.050~1.00", "영쩜영오영에서 일쩜영영"),
    ProbeCase("tilde_signed", "+1.50~2.00", "플러스 일쩜오영에서 이쩜영영"),
    ProbeCase(
        "tilde_signed_unit",
        "-0.050~+1.00kg",
        "마이너스 영쩜영오영에서 플러스 일쩜영영 킬로그램",
    ),
    ProbeCase("tilde_korean_tail", "1.50~2.0테스트", "일쩜오영에서 이쩜영 테스트"),
    ProbeCase("colon_decimal", "1.50:2.0", "일쩜오영 대 이쩜영"),
    ProbeCase(
        "colon_signed_plus",
        "+1.50:+2.00",
        "플러스 일쩜오영 대 플러스 이쩜영영",
    ),
    ProbeCase(
        "colon_signed_mixed",
        "-0.050:+1.00",
        "마이너스 영쩜영오영 대 플러스 일쩜영영",
    ),
    ProbeCase(
        "colon_comma_decimal",
        "1,000.50:2,000.50",
        "천쩜오영 대 이천쩜오영",
    ),
    ProbeCase(
        "multi_colon_decimal",
        "1.50:2.0:3.050",
        "일쩜오영 대 이쩜영 대 삼쩜영오영",
    ),
    ProbeCase("protected_backtick", "`1.50kg`", "`1.50kg`"),
    ProbeCase(
        "protected_json_price",
        '{"price":"USD1,000.50"}',
        '{"price":"USD1,000.50"}',
    ),
    ProbeCase("protected_json_temp", '{"temp":"+77.50°F"}', '{"temp":"+77.50°F"}'),
    ProbeCase("protected_json_range", '{"range":"1.50~2.0"}', '{"range":"1.50~2.0"}'),
    ProbeCase("protected_json_colon", '{"colon":"1.50:2.0"}', '{"colon":"1.50:2.0"}'),
    ProbeCase("protected_json_large", '{"large":"25.50억"}', '{"large":"25.50억"}'),
    ProbeCase("protected_path", "/path/USD1,000.50/log", "/path/USD1,000.50/log"),
    ProbeCase(
        "protected_url",
        "https://example.com?q=USD1,000.50",
        "https://example.com?q=USD1,000.50",
    ),
    ProbeCase("invalid_leading_zero_unit", "+01.50kg", "+01.50kg"),
    ProbeCase("invalid_comma_unit", "+1,00.50kg", "+1,00.50kg"),
    ProbeCase("invalid_usd_leading_zero", "USD+01.50", "USD+01.50"),
    ProbeCase("invalid_usd_comma", "USD+1,00.50", "USD+1,00.50"),
    ProbeCase("invalid_temperature", "+01.50℃", "+01.50℃"),
    ProbeCase("invalid_tilde", "+01.50~2", "+01.50~2"),
    ProbeCase("invalid_colon", "+01.50:2", "+01.50:2"),
    ProbeCase("malformed_large_dot", "25..50억", "25..50억"),
    ProbeCase("malformed_large_comma", "2,34억", "2,34억"),
    ProbeCase("malformed_large_double_comma", "2,,345억", "2,,345억"),
    ProbeCase("time_like_09_30", "09:30", "구시 삼십분"),
    ProbeCase("time_like_00_30", "00:30", "영시 삼십분"),
    ProbeCase("time_like_13_05", "13:05", "십삼시 오분"),
    ProbeCase("time_like_24_09", "24:09", "이십사시 구분"),
    ProbeCase("phone_domestic", "010-1234-5678", "공일공 일이삼사 오육칠팔"),
    ProbeCase(
        "phone_international",
        "+82-10-1234-5678",
        "플러스 팔이 일공 일이삼사 오육칠팔",
    ),
    ProbeCase("leading_zero_integer", "01", "01"),
    ProbeCase("leading_zero_integer_long", "001", "001"),
    ProbeCase("leading_zero_decimal", "01.5", "01.5"),
    ProbeCase("code_like_v01", "v01", "v01"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate ordinary decimal fractional zero reading across "
            "source/runtime paths."
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
    print("OK: no decimal fractional zero reading failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
