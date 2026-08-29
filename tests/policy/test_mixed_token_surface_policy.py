from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine.transform import transform_with_trace
from tests._policy_case import TextCase, assert_exact


MIXED_TOKEN_CASES = [
    TextCase("mixed-acronym-lexical-suffix-mfn-rate", "MFN율", "엠에프엔율", "mixed token", "atomic surface"),
    TextCase("mixed-acronym-lexical-suffix-kbs-reporter", "KBS기자", "케이비에스기자", "mixed token", "atomic surface"),
    TextCase("mixed-acronym-lexical-suffix-ai-based", "AI기반", "에이아이기반", "mixed token", "atomic surface"),
    TextCase("mixed-acronym-lexical-suffix-sk-hynix", "SK하이닉스", "에스케이하이닉스", "mixed token", "atomic surface"),
    TextCase("mixed-numeric-prefix-je-5-cha", "제5차", "제-오차", "mixed token", "atomic surface"),
    TextCase("mixed-numeric-prefix-je-62-hoe", "제62회", "제-육십이회", "mixed token", "atomic surface"),
    TextCase("mixed-numeric-suffix-60-yeo-myeong", "60여 명", "육십여 명", "mixed token", "atomic surface"),
    TextCase("mixed-numeric-large-13000-yeo-myeong", "1만3천여 명", "일만삼천여 명", "mixed token", "canonical leading one"),
    TextCase("mixed-numeric-versus-1-dae-1", "1대1", "일대일", "mixed token", "atomic surface"),
    TextCase("mixed-range-with-unit-3to8cm", "3에서 8cm", "삼에서 팔-센티미터", "mixed token", "atomic surface"),
    TextCase("mixed-range-with-unit-1to5cm", "1에서 5cm", "일에서 오-센티미터", "mixed token", "atomic surface"),
    TextCase("mixed-counter-spaced-large-number", "8만 9천 개", "팔만 구천-개", "mixed token", "atomic surface"),
]


@pytest.mark.parametrize("case", MIXED_TOKEN_CASES, ids=lambda case: case.case_id)
def test_mixed_token_atomic_surface_cases(case: TextCase):
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", MIXED_TOKEN_CASES, ids=lambda case: case.case_id)
def test_mixed_token_claims_are_owned_and_rendered_atomically(case: TextCase):
    output = transform_with_trace(case.text)
    assert output.trace.claim_logs
    assert any(claim.claim_type == "surface" for claim in output.trace.claim_logs)
    assert any(
        piece.provenance == "GENERATED_READING"
        for piece in output.render_pieces
    )
