from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1.2km", "일쩜이 킬로미터"),
        ("0.8초", "영쩜팔초"),
        ("3kg", "삼 킬로그램"),
        ("15g", "십오 그램"),
        ("250ml", "이백오십 밀리리터"),
        ("1L", "일 리터"),
        ("45㎡", "사십오 제곱미터"),
        ("45 ㎡", "사십오 제곱미터"),
        ("45m²", "사십오 제곱미터"),
        ("45m3", "사십오 세제곱미터"),
        ("45㎥", "사십오 세제곱미터"),
        ("2cm3", "이 세제곱센티미터"),
        ("3km3", "삼 세제곱킬로미터"),
        ("60Hz", "육십 헤르츠"),
        ("60hz", "육십 헤르츠"),
        ("120 Hz", "백이십 헤르츠"),
        ("3.2MHz", "삼쩜이 메가헤르츠"),
        ("3.2GHz", "삼쩜이 기가헤르츠"),
        ("5Ghz", "오 기가헤르츠"),
        ("12.5MB", "십이쩜오 메가바이트"),
        ("3.2GB", "삼쩜이 기가바이트"),
        ("1Gbps", "일 기가비피에스"),
        ("1Gb/s", "초당 일 기가바이트"),
        ("2.4PB", "이쩜사 페타바이트"),
        ("3.2kWh", "삼쩜이 킬로와트시"),
    ],
)
def test_simple_unit_policy_matrix(source: str, expected: str) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("45m3abc", "45m3abc"),
        ("30kgtest", "30kgtest"),
        ("5Hzabc", "5Hzabc"),
        ("5hzabc", "5hzabc"),
        ("30ºCtest", "30ºCtest"),
        ("40℉abc", "40℉abc"),
        ("Hz", "Hz"),
        ("hz", "hz"),
        ("A-3kg", "A-3kg"),
        ("K-2024", "K-2024"),
        ("USB300", "USB300"),
    ],
)
def test_simple_unit_unsafe_tail_preserve_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("90km/h", "시속 구십 킬로미터"),
        ("90㎞/h", "시속 구십 킬로미터"),
        ("5m/s", "초속 오 미터"),
        ("8.5m/min", "분속 팔쩜오 미터"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("15.2km/l", "리터당 십오쩜이 킬로미터"),
        ("15.2㎞/L", "리터당 십오쩜이 킬로미터"),
        ("15.2㎞/l", "리터당 십오쩜이 킬로미터"),
        ("15.2㎞/ℓ", "리터당 십오쩜이 킬로미터"),
        ("250m/L", "리터당 이백오십 미터"),
        ("3km/s", "초속 삼 킬로미터"),
        ("5cm/s", "초속 오 센티미터"),
    ],
)
def test_compound_unit_policy_matrix(source: str, expected: str) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("15.2km/La", "15.2km/La"),
        ("15.2km/lab", "15.2km/lab"),
        ("3km/speed", "3km/speed"),
        ("90km/hour", "90km/hour"),
        ("250m/Lite", "250m/Lite"),
        ("km/L", "km/L"),
        ("km/s", "km/s"),
        ("m/L", "m/L"),
    ],
)
def test_compound_unit_unsafe_tail_preserve_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("₩12,300", "만 이천삼백 원"),
        ("12,300원", "만 이천삼백 원"),
        ("3.5만 원", "삼쩜오 만 원"),
        ("1.2억 원", "일쩜이 억 원"),
        ("2.75억 원", "이쩜칠오 억 원"),
        ("1,250만 원", "천이백오십만 원"),
        ("2조 3,400억 원", "이조 삼천사백억 원"),
        ("$25.99", "이십오쩜구구 달러"),
        ("€1,234", "천이백삼십사 유로"),
        ("￥1,500", "천오백 엔"),
        ("300EUR", "삼백 유로"),
        ("EUR300", "삼백 유로"),
        ("€300", "삼백 유로"),
        ("300 €", "삼백 유로"),
        ("USD25.50", "이십오쩜오영 달러"),
        ("25.50USD", "이십오쩜오영 달러"),
    ],
)
def test_currency_policy_matrix(source: str, expected: str) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("EURA 300", "EURA 300"),
        ("300EURabc", "300EURabc"),
        ("USDX 300", "USDX 300"),
        ("USB300", "USB300"),
        ("KRWabc", "KRWabc"),
        ("€abc", "€abc"),
        ("$abc", "$abc"),
    ],
)
def test_currency_unsafe_tail_preserve_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://example.com/90km/h", "https://example.com/90km/h"),
        ("docs/2025/01/02/report.md", "docs/2025/01/02/report.md"),
        ("C:/Users/test/file.txt", "C:/Users/test/file.txt"),
        ("user@example.com", "user@example.com"),
        ("K-푸드 90km/h", "케이푸드 시속 구십 킬로미터"),
        (
            "URL https://example.com/90km/h 6월",
            "유알엘 https://example.com/90km/h 유월",
        ),
        (
            "비용은 $25.99이고 속도는 90km/h",
            "비용은 이십오쩜구구 달러이고 속도는 시속 구십 킬로미터",
        ),
    ],
)
def test_unit_currency_protected_span_and_adjacency_matrix(
    source: str, expected: str
) -> None:
    assert transform(source) == expected
