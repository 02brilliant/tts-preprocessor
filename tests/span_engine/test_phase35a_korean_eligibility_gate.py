from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "The temperature is 25℃.",
        "The price is $25.99.",
        "pH 7.4 was maintained for 3 hours.",
        "The ratio is 1/3 and the change is 2.5%p.",
        "Use 90km/h mode and 60Hz sampling.",
        '{"text":"25℃"}',
        "curl -X POST http://localhost:8010/api/transform",
        "https://example.com/a?x=1",
        "user@example.com",
        "/home/user/file.txt",
        'const value = "$25.99";',
    ],
)
def test_phase35a_global_no_hangul_bypass_exact_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("25℃", "이십오도"),
        ('$25.99', '이십오-쩜-구구-달러'),
        ("1/3", "삼분의 일"),
        ('2.5%p', '이-쩜-오-퍼센트포인트'),
        ("45m²", "사십오-제곱미터"),
        ('pH 7.4', '피에이치 칠-쩜-사'),
        ('pH7.4', '피에이치 칠-쩜-사'),
        ("60Hz", "육십-헤르츠"),
        ("3시간 18분", "세-시간 십팔분"),
        ("7시간05분", "일곱-시간 오분"),
    ],
)
def test_phase35a_standalone_supported_tokens_transform_without_hangul(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("오늘 온도는 25℃입니다.", "오늘 온도는 이십오도입니다."),
        ('가격은 $25.99로 표시됐다.', '가격은 이십오-쩜-구구-달러로 표시됐다.'),
        ('pH 7.4 조건에서 실험했다.', '피에이치 칠-쩜-사 조건에서 실험했다.'),
        ("경기 시간은 3시간 18분이었다.", "경기 시간은 세-시간 십팔분이었다."),
    ],
)
def test_phase35a_korean_mixed_sentence_remains_eligible(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_phase35a_numeric_list_line_in_korean_context_transforms() -> None:
    text = "오늘 관측값입니다.\n25℃, 3시간 18분, 2.5%p, 1/3, 45m², $25.99\n이상입니다."
    expected = (
        "오늘 관측값입니다.\n\n"
        "이십오도, 세-시간 십팔분, 이-쩜-오-퍼센트포인트, 삼분의 일, 사십오-제곱미터, 이십오-쩜-구구-달러 이상입니다."
    )
    assert transform(text) == expected


def test_phase35a_numeric_list_line_supports_compound_and_data_tokens() -> None:
    text = "측정값입니다.\n90km/h, 15.2km/L, 60Hz, pH 7.4, 2.4PB\n확인했습니다."
    expected = (
        "측정값입니다.\n\n"
        "시속 구십 킬로미터, 리터당 십오쩜이 킬로미터, 육십-헤르츠, 피에이치 칠-쩜-사, 이-쩜-사-페타바이트 확인했습니다."
    )
    assert transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "오늘 원문 인용입니다.\nThe temperature is 25℃ and pH 7.4.\n이상입니다.",
            "오늘 원문 인용입니다.\n\nThe temperature is 25℃ and pH 7.4.\n\n이상입니다.",
        ),
        (
            "오늘 관측값입니다.\n\n25℃, 3시간 18분",
            "오늘 관측값입니다.\n\n25℃, 3시간 18분",
        ),
        (
            '오늘 설정입니다.\n{"temp":"25℃","duration":"3시간 18분"}\n이상입니다.',
            '오늘 설정입니다.\n\n{"temp":"25℃","duration":"3시간 18분"} 이상입니다.',
        ),
    ],
)
def test_phase35a_numeric_list_adjacency_boundaries_preserve(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_phase35a_all_korean_lines_fast_path_regression_output() -> None:
    text = "오늘 온도는 25℃이고 경기 시간은 3시간 18분이었다.\n12.3 비상계엄과 90km/h이다."
    expected = "오늘 온도는 이십오도이고 경기 시간은 세-시간 십팔분이었다.\n\n십이삼 비상계엄과 시속 구십 킬로미터이다."
    assert transform(text) == expected
