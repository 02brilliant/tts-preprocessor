from __future__ import annotations

from engine.span_engine.transform import transform


MULTILINE_QUOTE_DELIMITERS = [
    ('"', '"'),
    ("“", "”"),
    ("'", "'"),
    ("‘", "’"),
]

MULTILINE_ENGLISH_BODIES = [
    "The temperature is 25℃.\npH 7.4 was maintained for 3 hours.",
    "The temperature is 25℃.\nThe ratio is 1/3.\nThe price is $25.99.",
    "Result: pH 7.4 was maintained for 3 hours.\nThe frequency was 60Hz.",
]

INLINE_CODE_SPANS = [
    '`"The temperature is 25℃."`',
    '`{"text":"25℃"}`',
    "`curl -X POST http://localhost:8010/api/transform`",
]

FENCED_BLOCKS = [
    '```json\n{"text":"25℃", "ph":"pH 7.4"}\n```',
    "```bash\ncurl -X POST http://localhost:8010/api/transform\n```",
    "```\nThe temperature is 25℃.\npH 7.4 was maintained for 3 hours.\n```",
]

VALID_CASES = [
    ("25℃", "이십오도"),
    ("pH 7.4", "피에이치 칠쩜사"),
    ("$25.99", "이십오쩜구구 달러"),
    ("1/3", "삼분의 일"),
    ("60Hz", "육십 헤르츠"),
    ("제2문항", "제 이문항"),
]


def _check_case(label: str, text: str, protected_literal: str, expected: str, tail: str) -> str | None:
    out = transform(text)
    if out == text:
        return f"{label}: output stayed raw\nTEXT={text}\nOUT={out}"
    if protected_literal not in out:
        return (
            f"{label}: protected literal missing or changed\n"
            f"PROTECTED={protected_literal}\nTEXT={text}\nOUT={out}"
        )
    if expected not in out:
        return f"{label}: outside valid surface did not transform\nEXPECTED={expected}\nTEXT={text}\nOUT={out}"
    if tail and tail not in out:
        return f"{label}: Korean tail was consumed by protected span\nTAIL={tail}\nTEXT={text}\nOUT={out}"
    return None


def _quote_cases() -> list[tuple[str, str, str]]:
    cases: list[tuple[str, str, str]] = []
    tails = ["라고 기록했고", "라는 문장을 남겼고", "도 원문으로 두었고"]
    for opener, closer in MULTILINE_QUOTE_DELIMITERS:
        for body in MULTILINE_ENGLISH_BODIES:
            literal = f"{opener}{body}{closer}"
            for tail in tails:
                cases.append((literal, literal, tail))
    return cases


def _code_cases() -> list[tuple[str, str, str]]:
    cases: list[tuple[str, str, str]] = []
    for literal in INLINE_CODE_SPANS:
        cases.append((literal, literal, "라고 입력했고"))
    for literal in FENCED_BLOCKS:
        cases.append((literal, literal, "다음 문장에서"))
    return cases


def main() -> None:
    failures: list[str] = []
    for protected_surface, protected_literal, tail in _quote_cases() + _code_cases():
        for valid, expected in VALID_CASES:
            text = (
                f"검증 문장입니다. {protected_surface}{tail}, "
                f"밖의 값 {valid}는 처리해야 합니다."
            )
            failure = _check_case(
                "protected_then_valid",
                text,
                protected_literal,
                expected,
                tail,
            )
            if failure:
                failures.append(failure)

            text = (
                f"검증 문장입니다. 밖의 값 {valid}는 처리하고, "
                f"{protected_surface}{tail}."
            )
            failure = _check_case(
                "valid_then_protected",
                text,
                protected_literal,
                expected,
                tail,
            )
            if failure:
                failures.append(failure)

    if failures:
        print(f"FAILURES: {len(failures)}")
        for index, failure in enumerate(failures[:100], 1):
            print("=" * 80)
            print("FAIL", index)
            print(failure)
        raise SystemExit(1)
    print("OK: no multiline markdown preserve failures")


if __name__ == "__main__":
    main()
