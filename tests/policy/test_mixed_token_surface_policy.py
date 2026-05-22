from __future__ import annotations

import pytest

from engine.pipeline.surfaces import SurfaceType
from engine.pipeline.transform_engine import normalize_text, transform_text
from tests._policy_case import TextCase, assert_exact


MIXED_TOKEN_CASES = [
    TextCase(
        case_id="mixed-acronym-lexical-suffix-mfn-rate",
        text="MFN율",
        expected="엠에프엔율",
        rule="mixed token / acronym + lexical suffix",
        reason="An acronym prefix plus lexical suffix must normalize as one atomic surface.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-acronym-lexical-suffix-kbs-reporter",
        text="KBS기자",
        expected="케이비에스기자",
        rule="mixed token / acronym + lexical suffix",
        reason="An acronym prefix plus lexical suffix must not leak raw uppercase letters into the final output.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-acronym-lexical-suffix-ai-based",
        text="AI기반",
        expected="에이아이기반",
        rule="mixed token / acronym + lexical suffix",
        reason="The acronym prefix must normalize without inserting an internal space before the lexical suffix.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-acronym-lexical-suffix-sk-hynix",
        text="SK하이닉스",
        expected="에스케이하이닉스",
        rule="mixed token / acronym + lexical suffix",
        reason="Acronym+lexical mixed tokens must be promoted before generic fallback even when the suffix is a proper noun tail.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-numeric-prefix-je-5-cha",
        text="제5차",
        expected="제오차",
        rule="mixed token / numeric prefixed noun",
        reason="Ordinal-like mixed tokens must consume the full surface rather than leaving the numeric core in raw form.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-numeric-prefix-je-62-hoe",
        text="제62회",
        expected="제육십이회",
        rule="mixed token / numeric prefixed noun",
        reason="Ordinal-like mixed tokens with larger values must normalize atomically.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-numeric-suffix-60-yeo-myeong",
        text="60여 명",
        expected="육십여 명",
        rule="mixed token / numeric suffixed noun",
        reason="The numeric core and suffix marker must normalize together instead of leaving a raw digit token behind.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-numeric-large-13000-yeo-myeong",
        text="1만3천여 명",
        expected="만 삼천여 명",
        rule="mixed token / numeric suffixed noun",
        reason="Compact large-unit digit expressions with 여 must normalize atomically.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-numeric-versus-1-dae-1",
        text="1대1",
        expected="일대일",
        rule="mixed token / numeric prefixed noun",
        reason="Versus-style mixed numeric tokens must normalize as one surface instead of leaking individual raw digits.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-range-with-unit-3to8cm",
        text="3에서 8cm",
        expected="삼에서 팔 센티미터",
        rule="mixed token / range with unit",
        reason="A spoken range plus unit must be consumed as one atomic surface instead of only normalizing the right unit token.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-range-with-unit-1to5cm",
        text="1에서 5cm",
        expected="일에서 오 센티미터",
        rule="mixed token / range with unit",
        reason="A spoken range plus unit must normalize both sides together.",
        classification="mixed_token",
    ),
    TextCase(
        case_id="mixed-counter-spaced-large-number",
        text="8만 9천 개",
        expected="팔만 구천 개",
        rule="mixed token / spaced large-number counter",
        reason="A spaced mixed large-number counter phrase must normalize before generic fallback can partially consume any component.",
        classification="mixed_token",
    ),
]


@pytest.mark.parametrize("case", MIXED_TOKEN_CASES, ids=lambda case: case.case_id)
def test_mixed_token_atomic_surface_cases(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("MFN율", "MFN율"),
        ("KBS기자", "KBS기자"),
        ("AI기반", "AI기반"),
        ("SK하이닉스", "SK하이닉스"),
        ("제5차", "제5차"),
        ("제62회", "제62회"),
        ("60여 명", "60여 명"),
        ("1만3천여 명", "1만3천여 명"),
        ("1대1", "1대1"),
        ("3에서 8cm", "3에서 팔 센티미터"),
        ("1에서 5cm", "1에서 오 센티미터"),
    ],
)
def test_mixed_token_partial_or_raw_residue_is_forbidden(text: str, forbidden: str):
    actual = transform_text(text)
    assert actual != forbidden, f"input={text!r} actual={actual!r}"


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("MFN율", SurfaceType.ACRONYM_WITH_LEXICAL_SUFFIX_SURFACE),
        ("제62회", SurfaceType.NUMERIC_PREFIXED_NOUN_SURFACE),
        ("3에서 8cm", SurfaceType.RANGE_WITH_UNIT_SURFACE),
    ],
)
def test_mixed_token_is_promoted_to_typed_surface(text: str, expected_type: SurfaceType):
    result = normalize_text(text)
    assert result.rendered_surfaces, f"input={text!r} rendered_surfaces should not be empty"
    assert result.rendered_surfaces[0].surface.surface_type == expected_type
