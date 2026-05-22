from __future__ import annotations

from engine.span_engine.transform import transform


VALID_CASES = [
    ("25℃", "이십오도"),
    ("pH 7.4", "피에이치 칠쩜사"),
    ("$25.99", "이십오쩜구구 달러"),
    ("₩12,300", "만 이천삼백 원"),
    ("3kg", "삼 킬로그램"),
    ("45㎡", "사십오 제곱미터"),
    ("60Hz", "육십 헤르츠"),
    ("2025-01-03", "이천이십오년 일월 삼일"),
    ("제2문항", "제 이문항"),
    ("K-푸드", "케이푸드"),
    ("A-10C", "에이 십 씨"),
]

PRESERVE_CASES = [
    ("The temperature is 25℃.", "The temperature is 25℃."),
    ("pH 7.4 was maintained for 3 hours.", "pH 7.4 was maintained for 3 hours."),
    (
        '"The temperature is 25℃ and pH 7.4 was maintained for 3 hours."',
        '"The temperature is 25℃ and pH 7.4 was maintained for 3 hours."',
    ),
    ('{"text":"25℃"}', '{"text":"25℃"}'),
    (
        "curl -X POST http://localhost:8010/api/transform",
        "curl -X POST http://localhost:8010/api/transform",
    ),
    ("https://example.com/a/b", "https://example.com/a/b"),
    ("docs/2025/01/02/report.md", "docs/2025/01/02/report.md"),
    ("C:/Users/test/file.txt", "C:/Users/test/file.txt"),
    ("user@example.com", "user@example.com"),
]

TEMPLATES = [
    "연구진은 {preserve}라는 문장을 원문으로 남겼고, 실제 값 {valid}는 처리해야 한다고 설명했다.",
    '연구진은 "{preserve}"라고 적었지만, 현장 값 {valid}는 처리해야 한다.',
    "문서에는 ({preserve})가 들어 있고, 본문에는 {valid}도 들어 있다.",
    "{preserve} 뒤에 {valid}가 이어지는 경우를 확인한다.",
    "{valid} 앞에 {preserve}가 붙어도 valid surface는 처리되어야 한다.",
]


def _expected_preserved_for_template(template: str, expected_preserved: str) -> str | None:
    # Parenthesis content is intentionally elided by current bracket policy.
    if "({preserve})" in template:
        return None
    return expected_preserved


def main() -> None:
    failures: list[tuple[str, str, str, str | None, str, str]] = []
    for valid, expected in VALID_CASES:
        for preserve, expected_preserved in PRESERVE_CASES:
            for template in TEMPLATES:
                text = template.format(valid=valid, preserve=preserve)
                out = transform(text)
                expected_preserved_for_template = _expected_preserved_for_template(
                    template, expected_preserved
                )
                preserve_missing = (
                    expected_preserved_for_template is not None
                    and expected_preserved_for_template not in out
                )
                if out == text or expected not in out or preserve_missing:
                    failures.append(
                        (
                            valid,
                            preserve,
                            expected,
                            expected_preserved_for_template,
                            text,
                            out,
                        )
                    )
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, (valid, preserve, expected, expected_preserved, text, out) in enumerate(
            failures[:100], 1
        ):
            print("=" * 80)
            print("FAIL", index)
            print("VALID:", valid)
            print("PRESERVE:", preserve)
            print("EXPECTED:", expected)
            print("EXPECTED_PRESERVED:", expected_preserved)
            print("TEXT:", text)
            print("OUT:", out)
        raise SystemExit(1)
    print("OK: no editorial inline preserve boundary failures")


if __name__ == "__main__":
    main()
