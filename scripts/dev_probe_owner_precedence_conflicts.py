from __future__ import annotations

from engine.span_engine.transform import transform


VALID_NEIGHBORS = [
    ("25℃", "이십오도"),
    ("pH 7.4", "피에이치 칠쩜사"),
    ("$25.99", "이십오쩜구구 달러"),
    ("3kg", "삼 킬로그램"),
]

CONFLICT_GROUPS = [
    {
        "name": "date_vs_code_separator",
        "surfaces": [
            ("2025-01-03", "이천이십오년 일월 삼일"),
            ("2026/06/17", "이천이십육년 유월 십칠일"),
            ("2025-13-03", "이공이오 일삼 공삼"),
            ("2025-01-32", "이공이오 공일 삼이"),
        ],
        "preserved": ["docs/2025/01/02/report.md"],
    },
    {
        "name": "event_vs_decimal_middle_dot",
        "surfaces": [
            ("12.3 비상계엄", "십이삼 비상계엄"),
            ("12·3 비상계엄", "십이삼 비상계엄"),
            ("12.12 사태", "십이십이 사태"),
            ("5·18 민주화 운동", "오일팔 민주화 운동"),
            ("13.3 비상계엄", "십삼쩜삼 비상계엄"),
            ("12.32 사태", "십이쩜삼이 사태"),
            ("12.3수치", "십이쩜삼수치"),
        ],
        "preserved": ["12 · 3"],
    },
    {
        "name": "currency_vs_number_code_like",
        "surfaces": [
            ("₩12,300", "만 이천삼백 원"),
            ("$25.99", "이십오쩜구구 달러"),
            ("300EUR", "삼백 유로"),
            ("EUR300", "삼백 유로"),
            ("USD25.50", "이십오쩜오영 달러"),
        ],
        "preserved": ["EURA 300", "300EURabc", "USDX 300", "USB300"],
    },
    {
        "name": "unit_compound_vs_path_code_like",
        "surfaces": [
            ("3kg", "삼 킬로그램"),
            ("45㎡", "사십오 제곱미터"),
            ("60Hz", "육십 헤르츠"),
            ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ],
        "preserved": [
            "docs/2025/01/02/report.md",
            "C:/Users/test/file.txt",
            "15.2km/La",
        ],
    },
    {
        "name": "emergency_counter_phone_hyphen",
        "surfaces": [
            ("112", "백십이"),
            ("119", "백십구"),
            ("1-1-2", "일 일 이"),
            ("1-1-9", "일 일 구"),
            ("112명", "백십이 명"),
            ("119건", "백십구 건"),
            ("112번 버스", "백십이번 버스"),
            ("119번 버스", "백십구번 버스"),
            ("010-1234-5678", "공일공 일이삼사 오육칠팔"),
            ("12-34-56", "일이 삼사 오육"),
        ],
        "preserved": ["1-2", "1-1 무"],
    },
    {
        "name": "signed_temperature_vs_hyphen_code",
        "surfaces": [
            ("-2.5℃", "영하 이쩜오도"),
            ("-2.5℉", "화씨 영하 이쩜오도"),
            ("+3℃", "영상 삼도"),
            ("온도-2.5℃", "온도영하 이쩜오도"),
        ],
        "preserved": ["A-2.5℃", "x-2.5℉", "B-2.5º"],
    },
    {
        "name": "ordinal_numeric_suffix_vs_counter",
        "surfaces": [
            ("제2문항", "제 이문항"),
            ("제 15권", "제 십오권"),
            ("2문항", "두 문항"),
            ("40문항", "사십 문항"),
            ("101문항", "백일 문항"),
        ],
        "preserved": ["제2문항abc", "제2.5문항"],
    },
]

TEMPLATES = [
    "검증 문장입니다. {surface} 표면과 {preserve} 후보가 있고, 주변 {neighbor} 값도 처리해야 합니다.",
    "검증 문장입니다. {preserve} 후보가 먼저 와도 {surface} 표면과 {neighbor} 값은 처리해야 합니다.",
    "앞에는 {neighbor}, 가운데에는 {preserve}, 뒤에는 {surface}가 있습니다.",
]


def main() -> None:
    failures: list[str] = []
    for group in CONFLICT_GROUPS:
        for surface, expected_surface in group["surfaces"]:
            for preserve in group["preserved"]:
                for neighbor, expected_neighbor in VALID_NEIGHBORS:
                    for template in TEMPLATES:
                        text = template.format(
                            surface=surface,
                            preserve=preserve,
                            neighbor=neighbor,
                        )
                        out = transform(text)
                        if (
                            out == text
                            or expected_surface not in out
                            or expected_neighbor not in out
                            or preserve not in out
                        ):
                            failures.append(
                                "\n".join(
                                    [
                                        f"GROUP={group['name']}",
                                        f"SURFACE={surface}",
                                        f"PRESERVE={preserve}",
                                        f"NEIGHBOR={neighbor}",
                                        f"EXPECTED_SURFACE={expected_surface}",
                                        f"EXPECTED_NEIGHBOR={expected_neighbor}",
                                        f"TEXT={text}",
                                        f"OUT={out}",
                                    ]
                                )
                            )
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, failure in enumerate(failures[:100], 1):
            print("=" * 80)
            print("FAIL", index)
            print(failure)
        raise SystemExit(1)
    print("OK: no owner precedence conflict failures")


if __name__ == "__main__":
    main()
