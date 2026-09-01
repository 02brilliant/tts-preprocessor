from __future__ import annotations

from engine.span_engine.transform import transform


def assert_local_degrade(
    text: str,
    expected_transformed: list[str],
    expected_preserved: list[str],
) -> None:
    out = transform(text)
    assert (
        out != text
    ), "Hangul-containing input with valid transform targets must not remain fully unchanged"
    for item in expected_transformed:
        assert item in out, f"expected transformed substring missing: {item!r}\nOUT={out}"
    for item in expected_preserved:
        assert item in out, f"expected preserved substring missing: {item!r}\nOUT={out}"


def test_invalid_prefixed_ordinal_does_not_block_neighbors() -> None:
    text = (
        "검증 문장입니다. 제2문항은 처리하고, 제 15권도 처리해야 합니다. "
        "하지만 제2-문항은 preserve되어야 합니다. "
        "동시에 pH 7.4와 25℃도 정상 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=["제-이문항", "제-십오권", "피에이치 칠-쩜-사", "이십오도"],
        expected_preserved=["제2-문항"],
    )


def test_invalid_currency_like_tokens_do_not_block_neighbors() -> None:
    text = (
        "결제 문장입니다. ₩12,300과 $25.99, €1,234, 300EUR, EUR300은 처리해야 합니다. "
        "하지만 EURA 300, 300EURabc, USDX 300, USB300, KRWabc, €abc, $abc는 preserve되어야 합니다. "
        "동시에 3kg과 pH 7.4도 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=[
            "만 이천삼백-원",
            "이십오-쩜-구구-달러",
            "천이백삼십사-유로",
            "삼백-유로",
            "삼-킬로그램",
            "피에이치 칠-쩜-사",
        ],
        expected_preserved=[
            "EURA 300",
            "300EURabc",
            "USDX 300",
            "USB300",
            "KRWabc",
            "€abc",
            "$abc",
        ],
    )


def test_percent_alias_unsafe_tail_does_not_block_neighbors() -> None:
    text = (
        "기술 문장입니다. 33.3％와 2.5％p, 2.5﹪p는 처리해야 합니다. "
        "하지만 2.5％pa와 2.5﹪point는 preserve되어야 합니다. "
        "동시에 25℃와 pH 7.4, 1／3도 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=[
            "삼십삼-쩜-삼-퍼센트",
            "이-쩜-오-퍼센트포인트",
            "이십오도",
            "피에이치 칠-쩜-사",
            "삼분의 일",
        ],
        expected_preserved=["2.5％pa", "2.5﹪point"],
    )


def test_square_bracket_preserve_does_not_block_outside_transform() -> None:
    text = (
        "괄호 검증입니다. [pH 7.4], [010-1234-5678], [2025-01-03], [ -2.5 ]는 내부 보호 대상입니다. "
        "하지만 괄호 밖 pH 7.4, 010-1234-5678, 2025-01-03, -2.5, 25℃는 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "피에이치 칠-쩜-사" in out
    assert "공일공 일이삼사 오육칠팔" in out
    assert "이천이십오년 일월 삼일" in out
    assert "이십오도" in out
    assert "pH 7.4" in out
    assert "010-1234-5678" in out
    assert "2025-01-03" in out


def test_inline_protected_spans_do_not_block_neighbors() -> None:
    text = (
        '개발팀은 {"text":"25℃"} JSON 조각과 curl -X POST http://localhost:8010/api/transform 명령을 예시로 들었습니다. '
        "문서 경로 docs/2025/01/02/report.md와 user@example.com은 preserve되어야 합니다. "
        "하지만 오늘 온도 25℃, 실험 조건 pH 7.4, 장비 무게 3kg, 가격 $25.99는 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=[
            "이십오도",
            "피에이치 칠-쩜-사",
            "삼-킬로그램",
            "이십오-쩜-구구-달러",
        ],
        expected_preserved=[
            '{"text":"25℃"}',
            "curl -X POST http://localhost:8010/api/transform",
            "docs/2025/01/02/report.md",
            "user@example.com",
        ],
    )


def test_url_path_code_like_preserve_does_not_block_neighbors() -> None:
    text = (
        "자료 문장입니다. https://example.com/a/b, C:/Users/test/file.txt, id_12345, model-X200, v1.2.3은 preserve되어야 합니다. "
        "하지만 45㎡, 1.2km, 60Hz, pH 7.4, ₩12,300은 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=[
            "사십오-제곱미터",
            "일-쩜-이-킬로미터",
            "육십-헤르츠",
            "피에이치 칠-쩜-사",
            "만 이천삼백-원",
        ],
        expected_preserved=[
            "https://example.com/a/b",
            "C:/Users/test/file.txt",
            "id_12345",
            "model-X200",
            "v1.2.3",
        ],
    )


def test_single_letter_code_invalid_tail_does_not_block_neighbors() -> None:
    text = (
        "장비 문장입니다. A-10C, K-1, K10, F-15C, K-21BC는 처리해야 합니다. "
        "하지만 K-2024, K-ABC, K-pop, A-10CAT, A-3kg은 preserve되어야 합니다. "
        "동시에 25℃와 3kg, pH 7.4도 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=[
            "에이-십 씨",
            "케이-원",
            "케이 십",
            "에프-십오 씨",
            "케이-이십일 비씨",
            "이십오도",
            "삼-킬로그램",
            "피에이치 칠-쩜-사",
        ],
        expected_preserved=["K-2024", "K-ABC", "K-pop", "A-10CAT", "A-3kg"],
    )


def test_compound_unit_invalid_tail_does_not_block_neighbors() -> None:
    text = (
        "교통 문장입니다. 90km/h, 15.2km/L, 3km/s, 10MB/s, 1Gb/s는 처리해야 합니다. "
        "하지만 15.2km/La, 15.2km/lab, 3km/speed, 90km/hour, 250m/Lite는 preserve되어야 합니다. "
        "동시에 25℃와 pH 7.4도 처리해야 합니다."
    )
    assert_local_degrade(
        text,
        expected_transformed=[
            "시속 구십 킬로미터",
            "리터당 십오쩜이 킬로미터",
            "초속 삼 킬로미터",
            "초당 십 메가바이트",
            "초당 일 기가바이트",
            "이십오도",
            "피에이치 칠-쩜-사",
        ],
        expected_preserved=[
            "15.2km/La",
            "15.2km/lab",
            "3km/speed",
            "90km/hour",
            "250m/Lite",
        ],
    )


def test_event_fail_candidates_do_not_block_neighbors() -> None:
    text = (
        "사건 검증입니다. 12.3 비상계엄, 12·3 비상계엄, 12.12 사태, 5·18 민주화 운동은 처리해야 합니다. "
        "하지만 13.3 비상계엄, 12.32 사태, 12.3수치, 12 · 3은 사건형 조건을 벗어납니다. "
        "동시에 pH 7.4와 25℃도 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "십이삼 비상계엄" in out
    assert "십이십이 사태" in out
    assert "오일팔 민주화 운동" in out
    assert "피에이치 칠-쩜-사" in out
    assert "이십오도" in out


def test_invalid_date_fallback_does_not_block_neighbors() -> None:
    text = (
        "일정 문장입니다. 2025-01-03과 2026/06/17은 날짜로 처리해야 합니다. "
        "하지만 2025-13-03, 2025-01-32, 2024-00-10, 2025/13/03은 invalid date fallback 경계를 확인합니다. "
        "동시에 pH 7.4와 25℃도 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "이천이십오년 일월 삼일" in out
    assert "이천이십육년 유월 십칠일" in out
    assert "피에이치 칠-쩜-사" in out
    assert "이십오도" in out
