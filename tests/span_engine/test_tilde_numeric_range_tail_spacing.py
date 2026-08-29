from __future__ import annotations

from engine.span_engine.transform import transform


def test_tilde_numeric_range_broad_reading() -> None:
    cases = [
        ("1~2", "일에서 이"),
        ("+1.5~2", "플러스 일쩜오에서 이"),
        ("3.410~3.56", "삼쩜사일영에서 삼쩜오육"),
        ("-2.480~3.24", "마이너스 이쩜사팔영에서 삼쩜이사"),
        ("-2.480~+3.24", "마이너스 이쩜사팔영에서 플러스 삼쩜이사"),
        ("+2.480~-3.24", "플러스 이쩜사팔영에서 마이너스 삼쩜이사"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_arbitrary_korean_tail_spacing() -> None:
    cases = [
        ("1~2테스트", "일에서 이 테스트"),
        ("1.2~3.4테스트", "일쩜이에서 삼쩜사 테스트"),
        ("-1.2~3.520테스트", "마이너스 일쩜이에서 삼쩜오이영 테스트"),
        ("-1.22~+3.520테스트", "마이너스 일쩜이이에서 플러스 삼쩜오이영 테스트"),
        ("+1.5~2테스트", "플러스 일쩜오에서 이 테스트"),
        ("+1.5~2 테스트", "플러스 일쩜오에서 이 테스트"),
        ("3.410~3.56범위", "삼쩜사일영에서 삼쩜오육 범위"),
        ("3.410~3.56 범위", "삼쩜사일영에서 삼쩜오육 범위"),
        ("1~2구간", "일에서 이 구간"),
        ("1~2 구간", "일에서 이 구간"),
        ("1~2숫자범위", "일에서 이 숫자범위"),
        ("1~2 숫자범위", "일에서 이 숫자범위"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_comma_decimal_blocks() -> None:
    cases = [
        ("+1,000.50~2,000.75 테스트", "플러스 천쩜오영에서 이천쩜칠오 테스트"),
        ("+1,000.50~2,000.75테스트", "플러스 천쩜오영에서 이천쩜칠오 테스트"),
        ("-1,000.50~+2,000.75 범위", "마이너스 천쩜오영에서 플러스 이천쩜칠오 범위"),
        ("-1,000.50~+2,000.75범위", "마이너스 천쩜오영에서 플러스 이천쩜칠오 범위"),
        ("+1,000.50~2,000.75.", "플러스 천쩜오영에서 이천쩜칠오."),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_optional_inline_whitespace() -> None:
    cases = [
        ("1 ~ 2 테스트", "일에서 이 테스트"),
        ("1 ~2테스트", "일에서 이 테스트"),
        ("1~ 2범위", "일에서 이 범위"),
        ("1.2 ~ 3.4구간", "일쩜이에서 삼쩜사 구간"),
        ("-1.2 ~ +3.520테스트", "마이너스 일쩜이에서 플러스 삼쩜오이영 테스트"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_non_ascii_tilde_tail_spacing() -> None:
    cases = [
        ("1～2테스트", "일에서 이 테스트"),
        ("1∼2테스트", "일에서 이 테스트"),
        ("1〜2테스트", "일에서 이 테스트"),
        ("+1.5〜2테스트", "플러스 일쩜오에서 이 테스트"),
        ("1.2～3.4범위", "일쩜이에서 삼쩜사 범위"),
        ("-1.2∼+3.520구간", "마이너스 일쩜이에서 플러스 삼쩜오이영 구간"),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_sentence_punctuation() -> None:
    cases = [
        ("1~2.", "일에서 이."),
        ("1.2~3.4.", "일쩜이에서 삼쩜사."),
        ("-1.2~+3.520.", "마이너스 일쩜이에서 플러스 삼쩜오이영."),
        ("문장 끝 range 1~2.", "문장 끝 range 일에서 이."),
        ("문장 끝 소수 range 1.2~3.4.", "문장 끝 소수 range 일쩜이에서 삼쩜사."),
        (
            "문장 끝 signed range -1.2~+3.520.",
            "문장 끝 signed range 마이너스 일쩜이에서 플러스 삼쩜오이영.",
        ),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_unit_tail_regression() -> None:
    cases = [
        ("+1.5~2kg", "플러스 일쩜오에서 이-킬로그램"),
        ("3.410~3.56cm", "삼쩜사일영에서 삼쩜오육-센티미터"),
        ("0.05~0.10cm", "영쩜영오에서 영쩜일영-센티미터"),
        ("1~2개", "일에서 이-개"),
        ("1~2원", "일에서 이-원"),
        ("1~2kg은", "일에서 이-킬로그램은"),
        ("0.05~0.10cm.", "영쩜영오에서 영쩜일영-센티미터."),
    ]
    for source, expected in cases:
        assert transform(source) == expected


def test_tilde_numeric_range_invalid_and_protected_preserve() -> None:
    for source in (
        "+01.5~2",
        "+1,00.5~2",
        "+.5~2",
        "1.~2",
        "3..140~4",
        "1~~2",
        "1~",
        "~2",
        "`1~2`",
        "`-2.480~3.24`",
        "/path/1~2/log",
        "/path/-2.480~3.24/log",
        "https://example.com?q=1~2",
        '{"range":"1~2"}',
        "v1~2",
        "file1~2.txt",
    ):
        assert transform(source) == source


def test_tilde_numeric_range_non_tilde_delimiters_unchanged() -> None:
    for source in (
        "1-2테스트",
        "1–2테스트",
        "1:2테스트",
        "1/2테스트",
        "-2.480-3.24",
        "-2.480–3.24",
    ):
        assert "에서" not in transform(source)


def test_tilde_numeric_range_long_integrated_sentences() -> None:
    source = (
        "입력값 1~2테스트와 1~2 테스트, 1.2~3.4범위와 1.2~3.4 범위, "
        "-1.2~3.520까지와 -1.2~3.520 까지, "
        "-1.22~+3.520구간과 -1.22~+3.520 구간을 모두 비교한다."
    )
    expected = (
        "입력값 일에서 이 테스트와 일에서 이 테스트, 일쩜이에서 삼쩜사 범위와 일쩜이에서 삼쩜사 범위, "
        "마이너스 일쩜이에서 삼쩜오이영까지와 마이너스 일쩜이에서 삼쩜오이영 까지, "
        "마이너스 일쩜이이에서 플러스 삼쩜오이영 구간과 마이너스 일쩜이이에서 플러스 삼쩜오이영 구간을 모두 비교한다."
    )
    assert transform(source) == expected

    source = (
        "백틱 `+1.5~2테스트`와 경로 /path/+1.5~2테스트/log는 그대로 두고, "
        "본문 +1.5~2테스트만 읽는다."
    )
    expected = (
        "백틱 `+1.5~2테스트`와 경로 /path/+1.5~2테스트/log는 그대로 두고, "
        "본문 플러스 일쩜오에서 이 테스트만 읽는다."
    )
    assert transform(source) == expected
