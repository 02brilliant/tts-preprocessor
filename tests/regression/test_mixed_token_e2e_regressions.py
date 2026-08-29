from __future__ import annotations

import re

import pytest

from engine.main import transform
from engine.main import transform
from tests._policy_case import TextCase, assert_exact


SENTENCE_CASES = [
    TextCase(
        case_id="mixed-sentence-mfn-rate",
        text="기존 MFN율을 그대로 내야 합니다.",
        expected="기존 엠에프엔율을 그대로 내야 합니다.",
        rule="mixed token / sentence regression",
        reason="Acronym+lexical suffix tokens must normalize inside ordinary prose.",
        classification="regression",
    ),
    TextCase(
        case_id="mixed-sentence-forum-ordinal-and-yeo",
        text="서울신라호텔에서 열린 '2025 제5차 포럼'에는 전문가 60여 명이 모였습니다.",
        expected="서울신라호텔에서 열린 '이천이십오 제-오차 포럼'에는 전문가 육십여 명이 모였습니다.",
        rule="mixed token / canonical ordinal and approximate marker",
        reason="The prefixed ordinal generates a space after 제 while the independent 여-marked number preserves its attachment.",
        classification="canonical",
    ),
    TextCase(
        case_id="mixed-sentence-large-counter",
        text="수출 중소기업도 8만 9천 개로 역대 최다를 기록했습니다.",
        expected="수출 중소기업도 팔만 구천-개로 역대 최다를 기록했습니다.",
        rule="mixed token / sentence regression",
        reason="A spaced mixed large-number counter phrase must normalize atomically in running text.",
        classification="regression",
    ),
    TextCase(
        case_id="mixed-sentence-ordinal-and-acronym-tail",
        text="제62회 무역의 날 기념식에선 SK하이닉스가 참여했습니다.",
        expected="제-육십이회 무역의 날 기념식에선 에스케이하이닉스가 참여했습니다.",
        rule="mixed token / canonical ordinal and acronym owners",
        reason="The prefixed ordinal and acronym claims render independently; the ordinal owner generates canonical spacing after 제.",
        classification="canonical",
    ),
    TextCase(
        case_id="mixed-sentence-large-yeo",
        text="내년 1만3천여 명을 대상으로 교육합니다.",
        expected="내년 일만삼천여 명을 대상으로 교육합니다.",
        rule="mixed token / canonical compact large-unit approximate",
        reason="The large-unit owner consumes the compact core as 일만삼천 and retains the attached approximate marker 여.",
        classification="canonical",
    ),
    TextCase(
        case_id="mixed-sentence-one-versus-one",
        text="강사가 1대1로 스마트폰 기초부터 가르칩니다.",
        expected="강사가 일대일로 스마트폰 기초부터 가르칩니다.",
        rule="mixed token / sentence regression",
        reason="Versus-style mixed numeric tokens must normalize in sentence context.",
        classification="regression",
    ),
    TextCase(
        case_id="mixed-sentence-range-with-unit",
        text="경기 북동부엔 3에서 8cm 서울 지역엔 1에서 5cm의 눈이 예상됩니다.",
        expected="경기 북동부엔 삼에서 팔-센티미터 서울 지역엔 일에서 오-센티미터의 눈이 예상됩니다.",
        rule="mixed token / sentence regression",
        reason="Spoken range plus unit surfaces must normalize atomically on both sides in running text.",
        classification="regression",
    ),
]


FULL_PIPELINE_CASES = [
    TextCase(
        case_id="mixed-full-pipeline-news-style",
        text="그리고 MFN율을 유지하면서 제62회 행사와 SK하이닉스 발표, 1만3천여 명 대상 교육, 3에서 8cm 적설 전망을 함께 설명했습니다.",
        expected="그리고, 엠에프엔율을 유지하면서 제-육십이회 행사와 에스케이하이닉스 발표, 일만삼천여 명 대상 교육, 삼에서 팔-센티미터 적설 전망을 함께 설명했습니다.",
        rule="mixed token / full pipeline regression",
        reason="Mixed-token typed surfaces must survive normalization and prosody together in one sentence.",
        classification="regression",
    ),
]


FORBIDDEN_RESIDUE_PATTERNS = [
    r"MFN율",
    r"KBS기자",
    r"AI기반",
    r"SK하이닉스",
    r"제5차",
    r"제62회",
    r"60여 명",
    r"1만3천여 명",
    r"1대1",
    r"3에서\s+팔\s+센티미터",
    r"1에서\s+오\s+센티미터",
]


@pytest.mark.parametrize("case", SENTENCE_CASES, ids=lambda case: case.case_id)
def test_mixed_token_sentence_regressions(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", FULL_PIPELINE_CASES, ids=lambda case: case.case_id)
def test_mixed_token_full_pipeline_regressions(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", SENTENCE_CASES, ids=lambda case: case.case_id)
def test_mixed_token_sentence_outputs_do_not_leave_raw_or_partial_residue(case: TextCase):
    actual = transform(case.text)
    for pattern in FORBIDDEN_RESIDUE_PATTERNS:
        assert re.search(pattern, actual) is None, f"input={case.text!r} pattern={pattern!r} actual={actual!r}"
