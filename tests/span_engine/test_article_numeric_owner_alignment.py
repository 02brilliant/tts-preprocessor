from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace


ARTICLE_INPUT = """기본계획은 3대 추진전략과 12개 세부 과제로 짜였다. 첫 번째 축은 AI 시대의 핵심 인프라인 공간정보를 다각도로 구축하는 것이다. 국토부는 AI 고속도로의 토대가 될 3차원 고정밀 핵심 공간정보 6종을 구축할 계획이다. 기존 5000분의 1 축척 중심의 2차원 지도에서 벗어나 전 국토를 고정밀 3차원 입체지도, 이른바 ‘신(新)대동여지도’로 새롭게 구축해 디지털 전환을 이뤄내고, 1000분의 1 지도 구축 범위도 넓힌다는 방침이다.
이렇게 확보한 3차원 고정밀 공간정보는 AI 학습데이터로도 활용된다. 국토부는 이를 토대로 공간을 분석해 의사결정을 지원하는 ‘GeoAI 파운데이션 모델’ 개발을 추진하고, 관련 연구개발(R&D) 투자도 늘리기로 했다. 위성 인프라 확충 계획도 눈에 띈다. 현재 운영 중인 국토위성 1·2호기에 더해 3·4호기를 추가로 도입하고, 기상 상황과 무관하게 상시 관측이 가능한 레이더 위성(SAR)도 새로 도입해 다양한 위성영상을 확보할 방침이다."""

ARTICLE_EXPECTED = """기본계획은 삼대 추진전략과 열두-개 세부 과제로 짜였다. 첫 번째 축은 에이아이 시대의 핵심 인프라인 공간정보를 다각도로 구축하는 것이다. 국토부는 에이아이 고속도로의 토대가 될 삼-차원 고정밀 핵심 공간정보 육종을 구축할 계획이다. 기존 오천분의 일 축척 중심의 이-차원 지도에서 벗어나 전 국토를 고정밀 삼-차원 입체지도, 이른바 ‘신대동여지도’로 새롭게 구축해 디지털 전환을 이뤄내고, 천분의 일 지도 구축 범위도 넓힌다는 방침이다.

이렇게 확보한 삼-차원 고정밀 공간정보는 에이아이 학습데이터로도 활용된다. 국토부는 이를 토대로 공간을 분석해 의사결정을 지원하는 ‘GeoAI 파운데이션 모델’ 개발을 추진하고, 관련 연구개발 투자도 늘리기로 했다. 위성 인프라 확충 계획도 눈에 띈다. 현재 운영 중인 국토위성 일·이호기에 더해 삼·사호기를 추가로 도입하고, 기상 상황과 무관하게 상시 관측이 가능한 레이더 위성도 새로 도입해 다양한 위성영상을 확보할 방침이다."""


def test_article_numeric_surfaces_are_fully_normalized() -> None:
    assert transform(ARTICLE_INPUT) == ARTICLE_EXPECTED


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5000분의 1 축척", "오천분의 일 축척"),
        ("1000분의 1 지도", "천분의 일 지도"),
        ("1,000분의 2", "천분의 이"),
        ("3 분의 1", "삼 분의 일"),
    ],
)
def test_textual_fraction_full_claim(text: str, expected: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    assert any(
        claim.owner == "textual_fraction"
        and claim.surface_type == "TEXTUAL_FRACTION_SURFACE"
        and claim.reason == "textual_fraction_full_consume_gate"
        for claim in output.trace.claim_logs
    )
    assert not any(
        claim.reason == "unsafe_korean_minute_second_suffix_preserve"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize("text", ["01분의 2", "1분의 0", "1,00분의 2"])
def test_invalid_textual_fraction_is_preserved_atomically(text: str) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == text
    assert any(
        claim.owner == "preserve"
        and claim.surface_type == "TEXTUAL_FRACTION_PRESERVE_SURFACE"
        and claim.reason == "textual_fraction_invalid_preserve"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("국토위성 1·2호기", "국토위성 일·이호기"),
        ("3·4호기를 도입한다", "삼·사호기를 도입한다"),
        ("1·2호", "1·2호"),
    ],
)
def test_middle_dot_equipment_sequence_precedence(
    text: str, expected: str
) -> None:
    output = transform_with_trace(text)

    assert output.normalized_text == expected
    if text.endswith("호"):
        assert not any(
            claim.owner == "middle_dot_numeric"
            for claim in output.trace.claim_logs
        )
    else:
        assert any(
            claim.owner == "middle_dot_numeric"
            and claim.reason == "middle_dot_numeric_block_match"
            for claim in output.trace.claim_logs
        )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3대 추진전략", "삼대 추진전략"),
        ("3대 전략", "삼대 전략"),
        ("3대 후보", "3대 후보"),
    ],
)
def test_dae_major_item_exact_anchor_expansion(text: str, expected: str) -> None:
    assert transform(text) == expected
