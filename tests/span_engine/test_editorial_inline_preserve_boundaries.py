from __future__ import annotations

from engine.span_engine.transform import transform


def assert_editorial_local_degrade(
    text: str,
    expected_transformed: list[str],
    expected_preserved: list[str],
) -> None:
    out = transform(text)
    assert out != text
    for item in expected_transformed:
        assert item in out, f"missing transformed substring: {item!r}\nOUT={out}"
    for item in expected_preserved:
        assert item in out, f"missing preserved substring: {item!r}\nOUT={out}"


def test_quoted_english_prose_sentence_does_not_block_korean_measurements() -> None:
    text = (
        '연구진은 "The temperature is 25℃ and pH 7.4 was maintained for 3 hours."라는 '
        "문장을 원문으로 남겼고, 실제 측정값 25℃와 pH 7.4는 처리해야 한다고 설명했다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["이십오도", "피에이치 칠-쩜-사"],
        expected_preserved=[
            '"The temperature is 25℃ and pH 7.4 was maintained for 3 hours."'
        ],
    )


def test_unquoted_english_sentence_before_korean_suffix_is_local_preserve() -> None:
    text = (
        "연구진은 The temperature is 25℃.라는 문구를 원문으로 남겼지만, "
        "현장 온도 25℃와 pH 7.4는 처리해야 한다고 적었다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["이십오도", "피에이치 칠-쩜-사"],
        expected_preserved=["The temperature is 25℃.", "라는 문구"],
    )


def test_quoted_english_ph_sentence_before_korean_ending_is_local_preserve() -> None:
    text = (
        '담당자는 "pH 7.4 was maintained for 3 hours."라고 설명했지만, '
        "한국어 본문의 pH 7.4와 $25.99는 처리해야 한다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["피에이치 칠-쩜-사", "이십오-쩜-구구-달러"],
        expected_preserved=['"pH 7.4 was maintained for 3 hours."'],
    )


def test_quoted_url_and_comma_do_not_block_neighbor_ph() -> None:
    text = (
        '문서에는 "https://example.com/a/b", 라는 URL이 들어 있고, '
        "본문의 pH 7.4와 25℃는 처리해야 한다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["피에이치 칠-쩜-사", "이십오도"],
        expected_preserved=['"https://example.com/a/b"'],
    )


def test_parenthesized_path_does_not_block_neighbor_temperature() -> None:
    text = (
        "문서에는 (docs/2025/01/02/report.md)와 별도 설명이 들어 있고, "
        "본문의 25℃와 3kg은 처리해야 한다."
    )
    out = transform(text)
    assert out != text
    assert "이십오도" in out
    assert "삼-킬로그램" in out
    assert "이천이십오" not in out


def test_email_with_korean_particle_does_not_block_currency() -> None:
    text = (
        "회계팀은 user@example.com으로 $25.99 영수증을 보냈고, "
        "같은 문장의 ₩12,300과 pH 7.4도 처리해야 한다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["이십오-쩜-구구-달러", "만 이천삼백-원", "피에이치 칠-쩜-사"],
        expected_preserved=["user@example.com"],
    )


def test_json_before_korean_ending_does_not_block_neighbors() -> None:
    text = (
        '{"text":"25℃"}라고 입력했다는 설명은 보존하고, '
        "실제 값 25℃와 pH 7.4, 제2문항은 처리해야 한다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["이십오도", "피에이치 칠-쩜-사", "제-이문항"],
        expected_preserved=['{"text":"25℃"}'],
    )


def test_backticked_curl_command_does_not_block_neighbors() -> None:
    text = (
        "`curl -X POST http://localhost:8010/api/transform` 명령 뒤에 "
        "pH 7.4와 25℃, A-10C를 넣었다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["피에이치 칠-쩜-사", "이십오도", "에이-십 씨"],
        expected_preserved=["curl -X POST http://localhost:8010/api/transform"],
    )


def test_preserve_valid_preserve_valid_sequence_survives() -> None:
    text = (
        '연구진은 {"text":"25℃"} 조각과 "The temperature is 25℃." 문구를 보존했다. '
        "하지만 본문 25℃와 pH 7.4, $25.99와 K-푸드는 처리해야 한다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["이십오도", "피에이치 칠-쩜-사", "이십오-쩜-구구-달러", "케이푸드"],
        expected_preserved=['{"text":"25℃"}', '"The temperature is 25℃."'],
    )


def test_code_like_tokens_with_quotes_and_commas_do_not_expand_span() -> None:
    text = (
        '"C:/Users/test/file.txt", "id_12345", "v1.2.3"은 보존하고, '
        "45㎡와 60Hz, 2025-01-03은 처리해야 한다."
    )
    assert_editorial_local_degrade(
        text,
        expected_transformed=["사십오-제곱미터", "육십-헤르츠", "이천이십오년 일월 삼일"],
        expected_preserved=["C:/Users/test/file.txt", "id_12345", "v1.2.3"],
    )
