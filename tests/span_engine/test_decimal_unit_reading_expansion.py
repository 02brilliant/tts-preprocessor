from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2.35명쯤", "이쩜삼오-명쯤"),
        ("2.35명정도", "이쩜삼오-명정도"),
        ("2.35명꼴", "이쩜삼오-명꼴"),
        ("2.35명당", "이쩜삼오-명당"),
        ("총 2.35번", "총 이쩜삼오-번"),
        ("책 2.35권", "책 이쩜삼오-권"),
        ("영화 2.35편", "영화 이쩜삼오-편"),
        ("2.35층 회의실", "이쩜삼오-층 회의실"),
        ("1.5가지", "일쩜오-가지"),
        ("1.5가지.", "일쩜오-가지."),
        ("5.5분 뒤", "오쩜오-분 뒤"),
        ("소요 시간 5.5분", "소요 시간 오쩜오-분"),
    ],
)
def test_valid_decimal_contextual_units_use_sino_decimal_reading(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("5.5분이 남았다", "오쩜오-분이 남았다"),
        ("2.35번 확인했다", "이쩜삼오-번 확인했다"),
        ("2.35권이 놓였다", "이쩜삼오-권이 놓였다"),
        ("2.35편이 공개됐다", "이쩜삼오-편이 공개됐다"),
        ("2.35층이 남았다", "이쩜삼오-층이 남았다"),
    ],
)
def test_decimal_contextual_units_follow_expanded_exact_anchors_or_defer(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("+2.35명", "플러스 이쩜삼오 명"),
        ("-2.35개", "마이너스 이쩜삼오 개"),
        ("–2.35명", "마이너스 이쩜삼오 명"),
        ("−2.35개", "마이너스 이쩜삼오 개"),
        ("총 +2.35번", "총 플러스 이쩜삼오 번"),
        ("책 -2.35권", "책 마이너스 이쩜삼오 권"),
        ("차량 +2.35대", "차량 플러스 이쩜삼오 대"),
    ],
)
def test_signed_decimal_counters_are_claimed_atomically(
    source: str, expected: str
) -> None:
    assert transform(source) == expected
    assert not any(sign in transform(source) for sign in ("+", "−", "–"))


@pytest.mark.parametrize(
    "source",
    [
        ".5명",
        "+.5명",
        "01.5명",
        "+01.5명",
        "1,00.5명",
        "1..5명",
        "1e-3kg",
        "1.5/2.5",
        "4A가지",
    ],
)
def test_noncanonical_decimal_and_code_like_surfaces_remain_preserved(
    source: str,
) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2.35kHz", "이쩜삼오-킬로헤르츠"),
        ("2.35KB", "이쩜삼오-킬로바이트"),
        ("2.35Mbps", "이쩜삼오 메가비피에스"),
        ("2.35rpm", "이쩜삼오 알피엠"),
        ("2.35fps", "이쩜삼오 에프피에스"),
        ("2.35ppm", "이쩜삼오 피피엠"),
        ("2.35ppb", "이쩜삼오 피피비"),
        ("2.35dBi", "이쩜삼오 디비아이"),
        ("10000.5kg", "만쩜오-킬로그램"),
        ("10,000.5kg", "만쩜오-킬로그램"),
    ],
)
def test_registered_units_share_valid_decimal_eligibility(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("pH 7.4.", "피에이치 칠쩜사."),
        ("pH +7.4", "피에이치 플러스 칠쩜사"),
        ("pH –7.4", "피에이치 마이너스 칠쩜사"),
        ("pH 7,400.25", "피에이치 칠천사백쩜이오"),
        ("pH 7,4", "pH 7,4"),
        ("pH 7..4", "pH 7..4"),
    ],
)
def test_ph_numeric_surface_is_full_consumed_or_preserved(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "2.35억–원",
        "2.35억—원",
        "2.35억−원",
        "2.35억＋원",
        "2.35억·원",
    ],
)
def test_large_unit_unapproved_delimiters_do_not_allow_partial_decimal_rewrite(
    source: str,
) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2.35m^2", "이쩜삼오-제곱미터"),
        ("2.35cm^3", "이쩜삼오-세제곱센티미터"),
        ("2.35KB^2", "이쩜삼오KB^2"),
        ("2.35foo^2", "이쩜삼오foo^2"),
        ("2.35m^4", "이쩜삼오m^4"),
        ("2.35kg^2", "이쩜삼오kg^2"),
        ("7V^3", "칠V^3"),
        ("m^3", "m^3"),
        ("7m ^3", "칠-미터 ^3"),
        ("7m^3.", "칠-세제곱미터."),
    ],
)
def test_caret_units_read_only_exact_natural_power_allowlist(
    source: str, expected: str
) -> None:
    assert transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [".5m^2", "01.5m^2", "1,00.5m^2", "1..5m^2"],
)
def test_caret_unit_malformed_numeric_surface_is_fully_preserved(
    source: str,
) -> None:
    assert transform(source) == source


@pytest.mark.parametrize(
    "source",
    [
        "`2.35명쯤`",
        "[총 2.35번]",
        '{"count":"+2.35명"}',
        "/path/2.35kg^2/file",
        "https://example.com/2.35KB^2",
    ],
)
def test_decimal_unit_expansion_keeps_protected_surfaces(source: str) -> None:
    expected = source[1:-1] if source.startswith("[") and source.endswith("]") else source
    assert transform(source) == expected


def test_signed_decimal_beon_keeps_residual_reading_and_spacing() -> None:
    source = "총 +2.35번"
    assert transform(source) == "총 플러스 이쩜삼오 번"
    result = transform_with_trace(source)
    assert any(piece.provenance == "GENERATED_READING" for piece in result.render_pieces)
