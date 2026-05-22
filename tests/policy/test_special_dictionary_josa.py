import pytest

from engine.pipeline.transform_engine import transform_text
from tests._policy_case import TextCase, assert_exact


SPECIAL_AND_DICTIONARY_CASES = [
    TextCase(
        case_id="special-hyphen-multi-block",
        text="123-456-7890",
        expected="일이삼 사오육 칠팔구공",
        rule="special format / hyphen digit blocks",
        reason="Three-block hyphen digit identifiers should read block by block with digit-wise readings.",
    ),
    TextCase(
        case_id="special-event-dictionary-surface",
        text="12.12 사태",
        expected="십이십이 사태",
        rule="special format / event phrase",
        reason="A documented event-number phrase must normalize as a protected event phrase rather than a decimal.",
    ),
    TextCase(
        case_id="special-event-dictionary-middle-dot-surface",
        text="5·18 민주화운동",
        expected="오일팔 민주화운동",
        rule="dictionary / longest match",
        reason="A fixed dictionary event surface should normalize exactly to its documented reading.",
    ),
    TextCase(
        case_id="special-emergency-bare-number-is-general-number",
        text="112",
        expected="백십이",
        rule="emergency number / plain general number",
        reason="Bare 112 has no emergency context, so policy requires the general numeric reading rather than 일일이.",
    ),
    TextCase(
        case_id="special-emergency-suffixed-number-is-general-number",
        text="112명",
        expected="백십이명",
        rule="emergency number / disallowed suffix",
        reason="명 is not an allowed emergency tail, so policy requires general-number fallback.",
    ),
    TextCase(
        case_id="special-ph-positive",
        text="pH 7.0",
        expected="피에이치 칠쩜영",
        rule="special format / pH",
        reason="A valid pH surface is explicitly supported and should normalize exactly.",
    ),
    TextCase(
        case_id="special-angle-positive",
        text="90°",
        expected="구십도",
        rule="special format / angle",
        reason="A degree-marked angle is an explicitly supported special format.",
    ),
    TextCase(
        case_id="special-d-number-protected",
        text="D-14",
        expected="D-14",
        rule="protection layer / D-number",
        reason="D-number surfaces are protected before the rule engine and must survive unchanged.",
    ),
    TextCase(
        case_id="special-snp-reading",
        text="S&P 500",
        expected="에스엔피 오백",
        rule="special format / S&P dynamic mapping",
        reason="S&P plus a number is a documented special mapping and not generic acronym fallback.",
    ),
    TextCase(
        case_id="special-snp-reading-alternate-surface",
        text="SNP 500",
        expected="에스엔피 오백",
        rule="special format / SNP dynamic mapping",
        reason="SNP is treated as the same documented dynamic mapping as S&P.",
    ),
    TextCase(
        case_id="dictionary-usb-longest-match",
        text="USB 3.0",
        expected="유에스비 삼쩜영",
        rule="dictionary / longest match first",
        reason="USB 3.0 is a longer fixed dictionary surface and must win over the shorter USB entry.",
    ),
    TextCase(
        case_id="dictionary-safe-acronym-fallback",
        text="LLM",
        expected="엘엘엠",
        rule="acronym fallback / positive",
        reason="An all-caps acronym missing from the fixed dictionary should fall back to letter-by-letter reading.",
    ),
    TextCase(
        case_id="dictionary-fixed-acronym-entry",
        text="CPU",
        expected="씨피유",
        rule="dictionary / fixed mapping",
        reason="A fixed dictionary acronym entry should resolve to its documented reading rather than generic fallback.",
    ),
    TextCase(
        case_id="dictionary-nonmatching-mixedcase-word-stays-original",
        text="OpenAI",
        expected="OpenAI",
        rule="acronym fallback / negative",
        reason="Mixed-case words outside the documented dictionary should not trigger the all-caps acronym fallback.",
    ),
    TextCase(
        case_id="dictionary-currency-wins-over-acronym-fallback",
        text="USD 100",
        expected="백 달러",
        rule="currency / precedence over acronym fallback",
        reason="A supported currency code must normalize as currency before any generic acronym fallback can run.",
    ),
]


PARTICLE_PRESERVATION_CASES = [
    TextCase(
        case_id="particle-preservation-acronym-topic",
        text="FTA은",
        expected="에프티에이은",
        rule="particle preservation / acronym",
        reason="The acronym may normalize, but the input particle must stay exactly as written.",
    ),
    TextCase(
        case_id="particle-preservation-acronym-subject",
        text="AI이",
        expected="에이아이이",
        rule="particle preservation / acronym",
        reason="Particle preservation forbids subject-particle correction after acronym normalization.",
    ),
    TextCase(
        case_id="particle-preservation-acronym-euro",
        text="MFN는",
        expected="엠에프엔는",
        rule="particle preservation / acronym",
        reason="Trailing particles are preserved metadata, not correction targets.",
    ),
    TextCase(
        case_id="particle-preservation-hangul-yuro",
        text="유로을",
        expected="유로을",
        rule="particle preservation / hangul literal",
        reason="Pure Hangul input is immutable, so post-processing must not rewrite the particle.",
    ),
    TextCase(
        case_id="particle-preservation-hangul-en",
        text="엔로",
        expected="엔로",
        rule="particle preservation / hangul literal",
        reason="Pure Hangul input is immutable, so particle correction is forbidden.",
    ),
    TextCase(
        case_id="particle-preservation-hangul-rieul",
        text="배럴으로",
        expected="배럴으로",
        rule="particle preservation / hangul literal",
        reason="Rieul exceptions are removed with particle correction; the original Hangul must remain unchanged.",
    ),
    TextCase(
        case_id="particle-preservation-hangul-al",
        text="알으로",
        expected="알으로",
        rule="particle preservation / hangul literal",
        reason="Pure Hangul counter words are immutable literals under the new core policy.",
    ),
]


@pytest.mark.parametrize("case", SPECIAL_AND_DICTIONARY_CASES, ids=lambda case: case.case_id)
def test_special_dictionary_policy(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", PARTICLE_PRESERVATION_CASES, ids=lambda case: case.case_id)
def test_particle_preservation_policy(case: TextCase):
    assert_exact(transform_text(case.text), case)
