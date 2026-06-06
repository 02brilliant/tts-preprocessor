from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.probes.runtime_matrix import (
    RuntimeRunner,
    add_runtime_filter_argument,
    build_runtime_runners,
)


@dataclass(frozen=True)
class ScenarioCase:
    name: str
    text: str
    exact: str | None = None
    contains: Tuple[str, ...] = ()
    not_contains: Tuple[str, ...] = ()
    preserves: Tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class ScenarioFailure:
    runner: str
    case_name: str
    text: str
    actual: str
    reason: str
    note: str = ""


GROUP_1_VALID = (
    "1",
    "+1",
    "-1",
    "1000",
    "+1000",
    "-1000",
    "1,000",
    "+1,000",
    "-1,000",
    "1.5",
    "+1.5",
    "-1.5",
    "0.05",
    "+0.05",
    "-0.05",
    "25.50",
    "+25.50",
    "-25.50",
    "1,000.50",
    "+1,000.50",
    "-2,500.75",
)
GROUP_1_INVALID_PRESERVE = (
    "01",
    "+01",
    "-01",
    "1,00",
    "1,00.5",
    "+1,00.5",
    "+.5",
    "-.5",
    "+1.",
    "1,0000",
)
GROUP_1_INVALID_AUDIT = (
    ScenarioCase("g01_leading_zero_malformed_decimal", "01.5", exact="01.5", note="leading_zero_malformed_decimal_preserve"),
    ScenarioCase("g01_plus_leading_zero_malformed_decimal", "+01.5", exact="+01.5", note="leading_zero_malformed_decimal_preserve"),
    ScenarioCase("g01_minus_leading_zero_malformed_decimal", "-01.5", exact="-01.5", note="leading_zero_malformed_decimal_preserve"),
    ScenarioCase("g01_long_leading_zero_malformed_decimal", "001.5", exact="001.5", note="leading_zero_malformed_decimal_preserve"),
    ScenarioCase("g01_plus_long_leading_zero_malformed_decimal", "+001.5", exact="+001.5", note="leading_zero_malformed_decimal_preserve"),
    ScenarioCase("g01_minus_long_leading_zero_malformed_decimal", "-001.5", exact="-001.5", note="leading_zero_malformed_decimal_preserve"),
    ScenarioCase("g01_current_trailing_dot", "1.", exact="일.", note="current_behavior"),
    ScenarioCase("g01_current_double_dot", "3..140", exact="삼..백사십", note="future malformed segmented reading candidate"),
)

GROUP_2_UNIT_PERCENT_VALID = (
    "+1.5kg",
    "+1.5 kg",
    "-2.0kg",
    "-2.0 kg",
    "+1,000.50kg",
    "+1,000.50 kg",
    "0.05cm",
    "0.05 cm",
    "-3.25m",
    "-3.25 m",
    "+25%",
    "+25 %",
    "-3.5%",
    "-3.5 %",
    "+1,000.50%",
    "+1,000.50 %",
    "0.05%",
    "0.05 %",
)
GROUP_2_SPACING_INVALID = (
    "+1.5  kg",
    "+1.5\tkg",
    "+25  %",
    "+25\t%",
    "1.5\nkg",
    "25\n%",
)
GROUP_2_INVALID = (
    "+01.5kg",
    "+01.5 kg",
    "+1,00.5kg",
    "+1,00.5 kg",
    "+.5kg",
    "+.5 kg",
    "1.kg",
    "1. kg",
    "+01.5%",
    "+01.5 %",
    "+1,00.5%",
    "+1,00.5 %",
    "+.5%",
    "+.5 %",
    "1.%",
    "1. %",
)

GROUP_3_TEMPERATURE_VALID = (
    "+25℃",
    "+25 ℃",
    "-3℃",
    "-3 ℃",
    "+77°F",
    "+77 °F",
    "화씨 +77°F",
    "화씨 +77 °F",
    "-10°F",
    "-10 °F",
    "+1.5℃",
    "+1.5 ℃",
    "-0.05℃",
    "-0.05 ℃",
    "+77.50°F",
    "+77.50 °F",
)
GROUP_3_TEMPERATURE_INVALID = (
    "+01.5℃",
    "+01.5 ℃",
    "+1,00.5℃",
    "+1,00.5 ℃",
    "+.5℃",
    "+.5 ℃",
    "1.℃",
    "1. ℃",
)

GROUP_4_KRW_EQUIVALENT = (
    "1,000원",
    "1,000 원",
    "KRW1000",
    "KRW1,000",
    "KRW 1,000",
    "₩1000",
    "₩1,000",
    "￦1,000",
    "1000KRW",
    "1,000KRW",
    "1,000 KRW",
)
GROUP_4_KRW_SIGNED_DECIMAL = (
    "+1,000.50원",
    "+1,000.50 원",
    "KRW+1,000.50",
    "KRW +1,000.50",
    "₩+1,000.50",
    "+₩1,000.50",
    "+1,000.50KRW",
    "+1,000.50 KRW",
    "-2,500.75원",
    "-2,500.75 원",
    "KRW-2,500.75",
    "KRW -2,500.75",
    "₩-2,500.75",
    "-₩2,500.75",
    "-2,500.75KRW",
    "-2,500.75 KRW",
)
GROUP_4_KRW_INVALID = (
    "+01.5원",
    "+01.5 원",
    "KRW+01.5",
    "KRW +01.5",
    "₩+01.5",
    "+₩01.5",
    "+01.5KRW",
    "+01.5 KRW",
    "+1,00.5원",
    "KRW+1,00.5",
    "₩+1,00.5",
    "+1,00.5KRW",
    "--₩1,000",
    "₩--1,000",
    "KRW+-1,000",
    "+-1,000원",
    "++1,000KRW",
)

GROUP_5_USD_EQUIVALENT = (
    "1,000달러",
    "1,000 달러",
    "USD1000",
    "USD1,000",
    "USD 1,000",
    "$1000",
    "$1,000",
    "1000USD",
    "1,000USD",
    "1,000 USD",
)
GROUP_5_USD_DECIMAL = (
    "1,000.50달러",
    "1,000.50 달러",
    "USD1000.50",
    "USD1,000.50",
    "USD 1,000.50",
    "$1000.50",
    "$1,000.50",
    "1000.50USD",
    "1,000.50USD",
    "1,000.50 USD",
)
GROUP_5_NON_KRW = (
    "1,000유로",
    "1,000 유로",
    "EUR1000",
    "EUR1,000",
    "EUR 1,000",
    "€1000",
    "€1,000",
    "1000EUR",
    "1,000EUR",
    "1,000 EUR",
    "1,000엔",
    "1,000 엔",
    "JPY1000",
    "JPY1,000",
    "JPY 1,000",
    "¥1000",
    "¥1,000",
    "￥1,000",
    "1000JPY",
    "1,000JPY",
    "1,000 JPY",
    "GBP1000",
    "GBP1,000",
    "GBP 1,000",
    "£1000",
    "£1,000",
    "1000GBP",
    "1,000GBP",
    "1,000 GBP",
)

GROUP_6_LARGE_UNIT_VALID = (
    "2345억",
    "2,345억",
    "2345만",
    "2,345만",
    "2345조",
    "2,345조",
    "2천8백28억",
    "3천4백61억",
    "1천2백3억",
    "4천5백6십7억",
    "8백28억",
    "28억",
    "25.50억",
    "+25.50억",
    "-25.50억",
    "1,000.50억",
    "+1,000.50억",
    "2천8백28.5억",
    "3천4백61.50억",
    "3천4백61억 원",
    "2천8백28억 원",
    "2,345억 원",
    "25.50억 원",
    "2천8백28억테스트",
    "2,345억테스트",
    "25.50억테스트",
    "2천8백28억abc",
    "2,345억abc",
    "25.50억abc",
)
GROUP_6_PREFIX_PRESERVE = (
    "v2천8백28억",
    "SKU2천8백28억",
    "abc2,345억",
)
GROUP_6_INVALID = (
    "2,34억",
    "2,,345억",
    "+.5억",
    "1.억",
    "25..50억",
    "2천8백..28억",
    "2천8백28..5억",
    "2천8백.28억",
)

GROUP_7_TILDE_VALID = (
    "1~2",
    "1~2테스트",
    "1~2 테스트",
    "1.2~3.4범위",
    "1.2~3.4 범위",
    "+1.5~2구간",
    "+1.5~2 구간",
    "-1.2~+3.520까지",
    "-1.22~+3.520구간",
    "1~2kg",
    "1~2 kg",
    "+1.5~2kg",
    "+1.5~2 kg",
    "-1.2~+3.4cm",
    "-1.2~+3.4 cm",
    "1～2테스트",
    "1∼2테스트",
    "1〜2테스트",
    "+1.5〜2테스트",
)
GROUP_7_TILDE_INVALID = (
    "+01.5~2",
    "+1,00.5~2",
    "+.5~2",
    "1.~2",
    "1~~2",
    "1~",
    "~2",
    "01.5~2테스트",
    "+1,00.5~2테스트",
)

GROUP_8_COLON_VALID = (
    "3:4",
    "3:4테스트",
    "3:4 테스트",
    "+1:2",
    "+1:2테스트",
    "+1:2 테스트",
    "1.5:2.0",
    "1.50:2.0",
    "+1.50:+2.0",
    "-1.50:+2.0",
    "1,000.50:2,000.50",
    "1:2:3",
    "1:2:3:4",
    "+1:2:-3:4",
    "1.0:2.0:3.0",
    "1.50:2.0:3.50",
    "+1.50:-2.0:+3.50",
)
GROUP_8_TIME_LIKE = (
    "00:30",
    "09:30",
    "13:05",
    "24:09",
    "24:50",
    "+1:02",
    "1:02:03",
    "오전 09:30",
    "오후 13:05",
    "line 1:23",
    "case 1:23",
    "version 1:23",
    "요한복음 3:16",
    "25:30",
    "13:5",
)
GROUP_8_COLON_INVALID = (
    "+01:2",
    "+1.:2",
    "+.5:2",
    "1,00:2",
    "03:4",
    "3:04",
    "01:2:3",
    "1:+2.:3",
    "1,00:2:3",
    "1:2:03:4",
    "1:2:3:4:5:6:7:8:9",
)

GROUP_9_HYPHEN_VALID = (
    "1-2kg",
    "1-2 kg",
    "1-2cm",
    "1-2 cm",
    "1-2개",
    "1-2 개",
    "1-2원",
    "1-2 원",
    "1-2kg.",
    "1-2kg은",
    "1-2kg의",
    "1-2kg까지",
)
GROUP_9_HYPHEN_PRESERVE = (
    "1-2테스트",
    "1-2 테스트",
    "1.5-2테스트",
    "1.5-2 테스트",
    "-1.5-2kg",
    "-1.5-2 kg",
    "+1.5-2kg",
    "+1.5-2 kg",
    "v1-2",
    "file-2025-01.txt",
    "1--2kg",
    "1-kg",
)

GROUP_10_PHONE = (
    "+82-10-1234-5678",
    "+1-800-123-4567",
)
GROUP_10_CODE_LIKE = (
    "+82-foo",
    "C++17",
    "A+B",
    "x+y=3",
    "foo+bar",
    "a+=1",
    "file-2025-01.txt",
)
GROUP_10_CURRENT_AUDIT = (
    ScenarioCase("g10_managed_version_hyphen_decimal", "version-1.5", exact="버전 일쩜오", note="managed_dictionary_numeric_code"),
)

GROUP_11_PROTECTED = (
    "`+1.5kg`",
    "`+25 %`",
    "`KRW1000`",
    "`₩1,000`",
    "`+25℃`",
    "`1~2테스트`",
    "`3:4테스트`",
    "`1-2kg`",
    "`2천8백28억`",
    "`2,345억`",
    "`25.50억`",
    '{"unit":"+1.5 kg"}',
    '{"percent":"+25 %"}',
    '{"price":"KRW1000"}',
    '{"price":"1,000원"}',
    '{"price":"USD 1,000"}',
    '{"temp":"+25℃"}',
    '{"range":"1~2테스트"}',
    '{"ratio":"3:4테스트"}',
    '{"large":"2천8백28억"}',
    '{"large":"2,345억"}',
    '{"hyphen":"1-2kg"}',
    "/path/+1.5kg/log",
    "/path/+25%/log",
    "/path/KRW1000/log",
    "/path/₩1,000/log",
    "/path/+25℃/log",
    "/path/1~2테스트/log",
    "/path/3:4테스트/log",
    "/path/1-2kg/log",
    "/path/2천8백28억/log",
    "/path/2,345억/log",
    "https://example.com?q=+1.5kg",
    "https://example.com?q=KRW1000",
    "https://example.com?q=₩1,000",
    "https://example.com?q=1~2테스트",
    "https://example.com?q=3:4테스트",
    "https://example.com?q=2천8백28억",
)

INTEGRATED_A = "통합 문장 A: 금액은 KRW1,000과 ₩1,000과 1,000원으로 쓰고, 해외 금액은 USD1,000과 $1,000과 1,000달러로 쓰며, 대단위 금액은 2천8백28억 원과 2,345억 원과 25.50억 원으로 쓰고, 무게는 +1.5 kg, 비율은 +25 %, 온도는 +25 ℃로 기록했다."
INTEGRATED_B = "통합 문장 B: 범위는 1~2kg과 +1.5~2 kg과 -1.2~+3.4 cm로 적었고, colon 값은 3:4테스트와 +1:2테스트와 1.50:2.0으로 적었으며, hyphen 값은 1-2kg과 1-2테스트를 함께 적었다."
INTEGRATED_C = '통합 문장 C: 보호 구간에는 `KRW1000`, `2천8백28억`, {"price":"1,000원"}, {"range":"1~2테스트"}, /path/2,345억/log, https://example.com?q=KRW1000이 있고, 문장 밖의 KRW1000, 2천8백28억, 1~2테스트는 처리되어야 한다.'
INTEGRATED_D = "통합 문장 D: invalid 입력 +01.5kg, +01.5 %, KRW+01.5, ₩+01.5, +01.5℃, +01.5~2, +01.5:2, 2,34억, 25..50억, 2천8백..28억, 1.5-2테스트는 부분 변환 없이 유지되어야 한다."


def joined(items: Iterable[str]) -> str:
    return "\n".join(items)


CASES = [
    ScenarioCase(
        "g01_signed_decimal_comma_valid",
        joined(GROUP_1_VALID),
        contains=(
            "일",
            "플러스 일",
            "마이너스 일",
            "천",
            "플러스 천",
            "마이너스 천",
            "일쩜오",
            "플러스 일쩜오",
            "마이너스 일쩜오",
            "영쩜영오",
            "플러스 영쩜영오",
            "마이너스 영쩜영오",
            "이십오쩜오영",
            "플러스 이십오쩜오영",
            "마이너스 이십오쩜오영",
            "천쩜오영",
            "플러스 천쩜오영",
            "마이너스 이천오백쩜칠오",
        ),
    ),
    ScenarioCase("g01_invalid_preserve", joined(GROUP_1_INVALID_PRESERVE), preserves=GROUP_1_INVALID_PRESERVE),
    *GROUP_1_INVALID_AUDIT,
    ScenarioCase(
        "g02_unit_percent_valid",
        joined(GROUP_2_UNIT_PERCENT_VALID),
        contains=(
            "플러스 일쩜오 킬로그램",
            "마이너스 이쩜영 킬로그램",
            "플러스 천쩜오영 킬로그램",
            "영쩜영오 센티미터",
            "마이너스 삼쩜이오 미터",
            "플러스 이십오 퍼센트",
            "마이너스 삼쩜오 퍼센트",
            "플러스 천쩜오영 퍼센트",
            "영쩜영오 퍼센트",
        ),
    ),
    ScenarioCase("g02_spacing_invalid_preserve", joined(GROUP_2_SPACING_INVALID), preserves=GROUP_2_SPACING_INVALID),
    ScenarioCase("g02_unit_percent_invalid_preserve", joined(GROUP_2_INVALID), preserves=GROUP_2_INVALID),
    ScenarioCase(
        "g03_temperature_sign_canonical",
        joined(GROUP_3_TEMPERATURE_VALID),
        contains=(
            "영상 이십오도",
            "영하 삼도",
            "화씨 영상 칠십칠도",
            "화씨 영하 십도",
            "영상 일쩜오도",
            "영하 영쩜영오도",
            "화씨 영상 칠십칠쩜오영도",
        ),
        not_contains=("플러스 이십오도", "마이너스 삼도", "플러스 칠십칠도", "마이너스 십도"),
    ),
    ScenarioCase("g03_temperature_invalid_preserve", joined(GROUP_3_TEMPERATURE_INVALID), preserves=GROUP_3_TEMPERATURE_INVALID),
    ScenarioCase("g04_krw_equivalence", joined(GROUP_4_KRW_EQUIVALENT), contains=("천 원",)),
    ScenarioCase(
        "g04_krw_signed_decimal",
        joined(GROUP_4_KRW_SIGNED_DECIMAL),
        contains=("플러스 천쩜오영 원", "마이너스 이천오백쩜칠오 원"),
    ),
    ScenarioCase("g04_krw_invalid_preserve", joined(GROUP_4_KRW_INVALID), preserves=GROUP_4_KRW_INVALID),
    ScenarioCase("g05_usd_equivalence", joined(GROUP_5_USD_EQUIVALENT), contains=("천 달러",)),
    ScenarioCase("g05_usd_decimal_trailing_zero", joined(GROUP_5_USD_DECIMAL), contains=("천쩜오영 달러",)),
    ScenarioCase("g05_non_krw_equivalence", joined(GROUP_5_NON_KRW), contains=("천 유로", "천 엔", "천 파운드")),
    ScenarioCase(
        "g06_large_unit_valid",
        joined(GROUP_6_LARGE_UNIT_VALID),
        contains=(
            "이천삼백사십오억",
            "이천삼백사십오만",
            "이천삼백사십오조",
            "이천팔백이십팔억",
            "삼천사백육십일억",
            "일천이백삼억",
            "사천오백육십칠억",
            "이십오쩜오영 억",
            "플러스 이십오쩜오영 억",
            "마이너스 이십오쩜오영 억",
            "이천팔백이십팔억 테스트",
            "이천팔백이십팔억abc",
        ),
    ),
    ScenarioCase("g06_prefix_preserve", joined(GROUP_6_PREFIX_PRESERVE), preserves=GROUP_6_PREFIX_PRESERVE),
    ScenarioCase("g06_invalid_preserve", joined(GROUP_6_INVALID), preserves=GROUP_6_INVALID, note="future malformed segmented reading candidates included"),
    ScenarioCase(
        "g07_tilde_valid",
        joined(GROUP_7_TILDE_VALID),
        contains=(
            "일에서 이",
            "일에서 이 테스트",
            "일쩜이에서 삼쩜사 범위",
            "플러스 일쩜오에서 이 구간",
            "플러스 일쩜오에서 이 테스트",
        ),
    ),
    ScenarioCase("g07_tilde_invalid_preserve", joined(GROUP_7_TILDE_INVALID), preserves=GROUP_7_TILDE_INVALID),
    ScenarioCase(
        "g08_colon_valid",
        joined(GROUP_8_COLON_VALID),
        contains=(
            "삼 대 사 테스트",
            "플러스 일 대 이 테스트",
        ),
    ),
    ScenarioCase(
        "g08_time_like_current_policy",
        joined(GROUP_8_TIME_LIKE),
        contains=("영시 삼십분", "구시 삼십분", "십삼시 오분", "이십사시 구분", "이십오 대 삼십"),
        preserves=("24:50", "+1:02", "1:02:03", "오후 13:05", "line 1:23", "case 1:23", "version 1:23", "요한복음 3:16"),
    ),
    ScenarioCase("g08_colon_invalid_preserve", joined(GROUP_8_COLON_INVALID), preserves=GROUP_8_COLON_INVALID, note="3:04 is checked separately as current time-like behavior"),
    ScenarioCase("g08_current_3_04_time_like", "3:04", exact="세시 사분", note="current_behavior"),
    ScenarioCase(
        "g09_hyphen_valid",
        joined(GROUP_9_HYPHEN_VALID),
        contains=("일에서 이 킬로그램", "일에서 이 개", "일에서 이 원", "일에서 이 킬로그램까지"),
    ),
    ScenarioCase("g09_hyphen_preserve", joined(GROUP_9_HYPHEN_PRESERVE), preserves=GROUP_9_HYPHEN_PRESERVE),
    ScenarioCase(
        "g10_phone",
        joined(GROUP_10_PHONE),
        contains=("플러스 팔이 일공 일이삼사 오육칠팔", "플러스 일 팔공공 일이삼 사오육칠"),
    ),
    ScenarioCase("g10_code_like_preserve", joined(GROUP_10_CODE_LIKE), preserves=GROUP_10_CODE_LIKE),
    *GROUP_10_CURRENT_AUDIT,
    ScenarioCase("g11_protected_preserve", joined(GROUP_11_PROTECTED), preserves=GROUP_11_PROTECTED),
    ScenarioCase(
        "g12_integrated_a",
        INTEGRATED_A,
        exact="통합 문장 A: 금액은 천 원과 천 원과 천 원으로 쓰고, 해외 금액은 천 달러과 천 달러과 천 달러로 쓰며, 대단위 금액은 이천팔백이십팔억 원과 이천삼백사십오억 원과 이십오쩜오영 억 원으로 쓰고, 무게는 플러스 일쩜오 킬로그램, 비율은 플러스 이십오 퍼센트, 온도는 영상 이십오도로 기록했다.",
    ),
    ScenarioCase(
        "g12_integrated_b",
        INTEGRATED_B,
        exact="통합 문장 B: 범위는 일에서 이 킬로그램과 플러스 일쩜오에서 이 킬로그램과 마이너스 일쩜이에서 플러스 삼쩜사 센티미터로 적었고, colon 값은 삼 대 사 테스트와 플러스 일 대 이 테스트와 일쩜오영 대 이쩜영으로 적었으며, hyphen 값은 일에서 이 킬로그램과 1-2테스트를 함께 적었다.",
    ),
    ScenarioCase(
        "g12_integrated_c",
        INTEGRATED_C,
        exact='통합 문장 C: 보호 구간에는 `KRW1000`, `2천8백28억`, {"price":"1,000원"}, {"range":"1~2테스트"}, /path/2,345억/log, https://example.com?q=KRW1000이 있고, 문장 밖의 천 원, 이천팔백이십팔억, 일에서 이 테스트는 처리되어야 한다.',
    ),
    ScenarioCase(
        "g12_integrated_d",
        INTEGRATED_D,
        exact="통합 문장 D: invalid 입력 +01.5kg, +01.5 %, KRW+01.5, ₩+01.5, +01.5℃, +01.5~2, +01.5:2, 2,34억, 25..50억, 2천8백..28억, 1.5-2테스트는 부분 변환 없이 유지되어야 한다.",
    ),
    ScenarioCase(
        "paragraph_long_single_korean",
        (
            "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
            "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
            "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
            "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
        ),
        contains=("\n", "한편"),
        note="production paragraph split after span transform",
    ),
    ScenarioCase(
        "paragraph_existing_newline",
        "첫 문장입니다.\n두 번째 문장입니다.",
        contains=("\n\n",),
        note="single newline normalized to paragraph boundary",
    ),
    ScenarioCase(
        "paragraph_long_numeric",
        (
            "보고서에는 12,345,678,901원과 3.5톤과 250m/L이 포함되어 "
            "재무팀과 물류팀이 함께 검토할 예정이며 이 문장은 의도적으로 길게 작성합니다. "
            "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
            "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
            "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
            "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
        ),
        contains=("\n", "삼쩜오톤", "리터당", "한편"),
        not_contains=("3.5톤", "250m/L"),
        note="numeric readings preserved across paragraph split",
    ),
    ScenarioCase(
        "paragraph_protected_inline",
        (
            "설명은 https://example.com/v1/items 경로와 "
            '{"enabled": true, "retry": 3} 설정과 `curl -X POST` 명령을 참고합니다. '
            "첫 번째 설명은 현재 정책 검증을 위해 충분히 길게 작성되어 여러 조건과 배경을 차분하게 이어서 말합니다. "
            "두 번째 설명도 같은 주제를 이어 가며 일정과 예산과 결과를 자세히 정리하여 전체 문단 길이를 안정적으로 늘립니다. "
            "세 번째 설명 역시 앞선 내용과 같은 흐름을 유지하며 독자가 숫자와 일반 서술을 함께 듣는 상황을 가정합니다. "
            "한편 마지막 설명은 다른 주제로 전환되어 후속 계획과 검토 항목을 분명하게 알립니다."
        ),
        preserves=(
            "https://example.com/v1/items",
            '"enabled": true',
            "`curl -X POST`",
        ),
        contains=("\n", "한편"),
        note="protected spans preserved; split only at outer sentence boundaries",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate long 12-group scenario regression examples."
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


def check_case(
    runner_name: str,
    runner: Callable[[str], str],
    case: ScenarioCase,
) -> ScenarioFailure | None:
    try:
        actual = runner(case.text)
    except Exception as exc:
        return ScenarioFailure(
            runner=runner_name,
            case_name=case.name,
            text=case.text,
            actual="",
            reason=f"{type(exc).__name__}: {exc}",
            note=case.note,
        )

    if case.exact is not None and actual != case.exact:
        return ScenarioFailure(
            runner=runner_name,
            case_name=case.name,
            text=case.text,
            actual=actual,
            reason=f"exact mismatch: expected={case.exact!r}",
            note=case.note,
        )

    missing = tuple(fragment for fragment in case.contains if fragment not in actual)
    if missing:
        return ScenarioFailure(
            runner=runner_name,
            case_name=case.name,
            text=case.text,
            actual=actual,
            reason=f"missing contains fragments={missing!r}",
            note=case.note,
        )

    unexpected = tuple(fragment for fragment in case.not_contains if fragment in actual)
    if unexpected:
        return ScenarioFailure(
            runner=runner_name,
            case_name=case.name,
            text=case.text,
            actual=actual,
            reason=f"unexpected fragments={unexpected!r}",
            note=case.note,
        )

    not_preserved = tuple(surface for surface in case.preserves if surface not in actual)
    if not_preserved:
        return ScenarioFailure(
            runner=runner_name,
            case_name=case.name,
            text=case.text,
            actual=actual,
            reason=f"not preserved surfaces={not_preserved!r}",
            note=case.note,
        )

    return None


def format_failure(failure: ScenarioFailure) -> str:
    lines = [
        f"[FAIL] runner={failure.runner}",
        f"case={failure.case_name}",
        f"input={failure.text!r}",
        f"reason={failure.reason}",
        f"actual={failure.actual!r}",
    ]
    if failure.note:
        lines.append(f"note={failure.note}")
    return "\n".join(lines)


def run_cases(runner_name: str, runner: Callable[[str], str]) -> ScenarioFailure | None:
    for case in CASES:
        failure = check_case(runner_name, runner, case)
        if failure is not None:
            return failure
    return None


def main() -> int:
    args = parse_args()
    try:
        runners: list[RuntimeRunner] = build_runtime_runners(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    for runner_name, runner in runners:
        failure = run_cases(runner_name, runner)
        if failure is not None:
            print(format_failure(failure))
            return 1

    print("OK: no 12-group scenario regression failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
