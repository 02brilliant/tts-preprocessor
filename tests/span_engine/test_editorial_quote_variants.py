from __future__ import annotations

from engine.span_engine.transform import transform


def assert_preserve_and_transform(text: str, preserved: list[str], transformed: list[str]) -> None:
    out = transform(text)
    assert out != text
    for value in preserved:
        assert value in out, f"missing preserved {value!r}\nOUT={out}"
    for value in transformed:
        assert value in out, f"missing transformed {value!r}\nOUT={out}"


def test_single_quoted_english_prose_preserved_but_outside_values_transform() -> None:
    text = "'The temperature is 25℃.'라는 문구를 원문으로 남기고, 실제 온도 25℃와 pH 7.4는 처리해야 합니다."
    assert_preserve_and_transform(
        text,
        preserved=["The temperature is 25℃."],
        transformed=["이십오도", "피에이치 칠쩜사"],
    )


def test_smart_quoted_english_prose_preserved_but_outside_values_transform() -> None:
    text = "연구진은 “pH 7.4 was maintained for 3 hours.”라고 적었고, 실제 조건 pH 7.4와 25℃는 처리해야 합니다."
    assert_preserve_and_transform(
        text,
        preserved=["pH 7.4 was maintained for 3 hours."],
        transformed=["피에이치 칠쩜사", "이십오도"],
    )


def test_multi_sentence_quote_preserved() -> None:
    text = '"The temperature is 25℃. pH 7.4 was maintained for 3 hours. The ratio is 1/3."라고 적고, 본문 값 25℃와 1/3은 처리해야 합니다.'
    assert_preserve_and_transform(
        text,
        preserved=[
            "The temperature is 25℃. pH 7.4 was maintained for 3 hours. The ratio is 1/3."
        ],
        transformed=["이십오도", "삼분의 일"],
    )


def test_semicolon_english_prose_preserved() -> None:
    text = "원문은 The temperature is 25℃; pH 7.4 was maintained for 3 hours.라고 남기고, 실제 값 pH 7.4는 처리해야 합니다."
    assert_preserve_and_transform(
        text,
        preserved=["The temperature is 25℃; pH 7.4 was maintained for 3 hours."],
        transformed=["피에이치 칠쩜사"],
    )


def test_colon_english_prose_preserved() -> None:
    text = "보고서에는 Result: pH 7.4 was maintained for 3 hours.라고 쓰였고, 측정값 pH 7.4와 $25.99는 처리해야 합니다."
    assert_preserve_and_transform(
        text,
        preserved=["Result: pH 7.4 was maintained for 3 hours."],
        transformed=["피에이치 칠쩜사", "이십오쩜구구-달러"],
    )


def test_quote_boundary_does_not_consume_korean_particles() -> None:
    text = '"The temperature is 25℃."라는 표현과 "pH 7.4 was maintained."도 원문으로 두고, 밖의 25℃는 처리합니다.'
    out = transform(text)
    assert '"The temperature is 25℃."' in out or "The temperature is 25℃." in out
    assert "라는 표현" in out
    assert "도 원문" in out
    assert "이십오도" in out
