from __future__ import annotations

from engine.span_engine.transform import transform


QUOTE_FORMATS = [
    ('"{}"', "{}"),
    ("'{}'", "{}"),
    ("“{}”", "{}"),
    ("‘{}’", "{}"),
]

ENGLISH_PROSE_SPANS = [
    "The temperature is 25℃.",
    "pH 7.4 was maintained for 3 hours.",
    "The temperature is 25℃; pH 7.4 was maintained for 3 hours.",
    "Result: pH 7.4 was maintained for 3 hours.",
    "The temperature is 25℃. pH 7.4 was maintained for 3 hours. The ratio is 1/3.",
]

KOREAN_TAILS = [
    "라는 문구",
    "라고 설명했다",
    "은 원문이다",
    "도 유지한다",
    "와 비교했다",
]

VALID_SURFACES = [
    ("25℃", "이십오도"),
    ("pH 7.4", "피에이치 칠쩜사"),
    ("$25.99", "이십오쩜구구 달러"),
    ("1/3", "삼분의 일"),
    ("60Hz", "육십 헤르츠"),
]


def main() -> None:
    failures: list[tuple[str, str, str, str, str, str]] = []
    for quote_template, expected_template in QUOTE_FORMATS:
        for prose in ENGLISH_PROSE_SPANS:
            quoted = quote_template.format(prose)
            expected_preserved = expected_template.format(prose)
            for tail in KOREAN_TAILS:
                for valid, expected_valid in VALID_SURFACES:
                    text = (
                        f"연구진은 {quoted}{tail}. "
                        f"실제 본문 값 {valid}는 처리해야 합니다."
                    )
                    out = transform(text)
                    if (
                        out == text
                        or expected_preserved not in out
                        or expected_valid not in out
                        or tail not in out
                    ):
                        failures.append(
                            (quoted, tail, valid, expected_valid, text, out)
                        )
    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, (quoted, tail, valid, expected_valid, text, out) in enumerate(
            failures[:100], 1
        ):
            print("=" * 80)
            print("FAIL", index)
            print("QUOTED:", quoted)
            print("TAIL:", tail)
            print("VALID:", valid)
            print("EXPECTED_VALID:", expected_valid)
            print("TEXT:", text)
            print("OUT:", out)
        raise SystemExit(1)
    print("OK: no editorial quote variant failures")


if __name__ == "__main__":
    main()
