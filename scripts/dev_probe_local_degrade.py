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
    ("010-1234-5678", "공일공 일이삼사 오육칠팔"),
    ("제2문항", "제 이문항"),
    ("1／3", "삼분의 일"),
    ("90km／h", "시속 구십 킬로미터"),
    ("K-푸드", "케이푸드"),
    ("A-10C", "에이 십 씨"),
]

PRESERVE_CASES = [
    ('{"text":"25℃"}', '{"text":"25℃"}'),
    ("curl -X POST http://localhost:8010/api/transform", "curl -X POST http://localhost:8010/api/transform"),
    ("user@example.com", "user@example.com"),
    ("docs/2025/01/02/report.md", "docs/2025/01/02/report.md"),
    ("C:/Users/test/file.txt", "C:/Users/test/file.txt"),
    ("id_12345", "id_12345"),
    ("model-X200", "model-X200"),
    ("v1.2.3", "v1.2.3"),
    ("제2.5문항", "제2.5문항"),
    ("제2-문항", "제2-문항"),
    ("제2문항abc", "제2문항abc"),
    ("A제 2문항", "A제 2문항"),
    ("300EURabc", "300EURabc"),
    ("EURA 300", "EURA 300"),
    ("USDX 300", "USDX 300"),
    ("USB300", "USB300"),
    ("KRWabc", "KRWabc"),
    ("€abc", "€abc"),
    ("$abc", "$abc"),
    ("2.5％pa", "2.5％pa"),
    ("2.5﹪point", "2.5﹪point"),
    ("15.2km/La", "15.2km/La"),
    ("3km/speed", "3km/speed"),
    ("250m/Lite", "250m/Lite"),
    ("[pH 7.4]", "pH 7.4"),
    ("[010-1234-5678]", "010-1234-5678"),
    ("[2025-01-03]", "2025-01-03"),
    ("[ -2.5 ]", " -2.5 "),
    ("K-2024", "K-2024"),
    ("K-ABC", "K-ABC"),
    ("K-pop", "K-pop"),
    ("A-10CAT", "A-10CAT"),
    ("A-3kg", "A-3kg"),
]

TEMPLATES = [
    "검증 문장입니다. {preserve} 조각은 보존하고, {valid} 값은 처리해야 합니다.",
    "검증 문장입니다. {valid} 값은 처리하고, {preserve} 조각은 보존해야 합니다.",
    "앞 문장에는 {preserve}가 있고 뒤 문장에는 {valid}가 있습니다.",
    "{preserve} 바로 뒤에 {valid}가 이어지는 경우도 확인합니다.",
    "{valid} 바로 뒤에 {preserve}가 이어지는 경우도 확인합니다.",
]


def main() -> None:
    failures: list[tuple[str, str, str, str, str, str]] = []
    for valid, expected in VALID_CASES:
        for preserve, expected_preserved in PRESERVE_CASES:
            for template in TEMPLATES:
                text = template.format(valid=valid, preserve=preserve)
                out = transform(text)
                if out == text or expected not in out or expected_preserved not in out:
                    failures.append((valid, preserve, expected, expected_preserved, text, out))
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
    print("OK: no local degrade failures")


if __name__ == "__main__":
    main()
