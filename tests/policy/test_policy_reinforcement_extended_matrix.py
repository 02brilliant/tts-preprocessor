import pytest

from engine.pipeline.transform_engine import transform_text
from tests._policy_case import TextCase, assert_exact


ACRONYM_PARTICLE_PRESERVATION_CASES = [
    TextCase(
        case_id="acronym-particle-preserve-fta-topic",
        text="FTA은",
        expected="에프티에이은",
        rule="policy / acronym protected output + particle preservation",
        reason="Acronym normalization may change the Latin stem, but the input Hangul particle must stay exactly as written.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-fta-subject",
        text="FTA이",
        expected="에프티에이이",
        rule="policy / acronym protected output + particle preservation",
        reason="Particle correction is forbidden even when the source stem is an acronym.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-fta-euro",
        text="FTA으로",
        expected="에프티에이으로",
        rule="policy / acronym protected output + particle preservation",
        reason="The input particle must be preserved verbatim instead of being batchim-adjusted.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-ai-topic",
        text="AI은",
        expected="에이아이은",
        rule="policy / acronym protected output + particle preservation",
        reason="Particle preservation applies equally to dictionary-backed acronym readings.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-ai-subject",
        text="AI이",
        expected="에이아이이",
        rule="policy / acronym protected output + particle preservation",
        reason="Particle correction is forbidden after acronym normalization.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-ai-euro",
        text="AI으로",
        expected="에이아이으로",
        rule="policy / acronym protected output + particle preservation",
        reason="The trailing Hangul particle remains immutable metadata.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-iso-comitative",
        text="ISO과",
        expected="아이에스오과",
        rule="policy / acronym protected output + particle preservation",
        reason="Comitative particle correction is forbidden under the core invariance principle.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-iec-comitative",
        text="IEC과",
        expected="아이이씨과",
        rule="policy / acronym protected output + particle preservation",
        reason="Trailing particles must not be rewritten after the acronym body is normalized.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-mfn-topic",
        text="MFN는",
        expected="엠에프엔는",
        rule="policy / acronym protected output + particle preservation",
        reason="Incorrect input particles are preserved rather than corrected.",
        classification="post_processing",
    ),
    TextCase(
        case_id="acronym-particle-preserve-mfn-object",
        text="MFN를",
        expected="엠에프엔를",
        rule="policy / acronym protected output + particle preservation",
        reason="The output must preserve the original particle instead of selecting a corrected pair.",
        classification="post_processing",
    ),
]


ACRONYM_OUTPUT_INTERACTION_CASES = [
    TextCase(
        case_id="acronym-protected-fta-object",
        text="FTA를",
        expected="에프티에이를",
        rule="policy / acronym protected output interaction",
        reason="Acronym outputs must remain compact under normal object-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-fta-comitative",
        text="FTA와",
        expected="에프티에이와",
        rule="policy / acronym protected output interaction",
        reason="Acronym outputs must remain compact under normal comitative-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-ai-object",
        text="AI를",
        expected="에이아이를",
        rule="policy / acronym protected output interaction",
        reason="Acronym outputs must remain compact under normal object-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-ai-comitative",
        text="AI와",
        expected="에이아이와",
        rule="policy / acronym protected output interaction",
        reason="Acronym outputs must remain compact under normal comitative-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-mfn-object",
        text="MFN을",
        expected="엠에프엔을",
        rule="policy / acronym protected output interaction",
        reason="Acronym outputs must remain compact under normal object-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-mfn-euro",
        text="MFN으로",
        expected="엠에프엔으로",
        rule="policy / acronym protected output interaction",
        reason="Acronym outputs must remain compact under normal 으로/로 attachment when the final reading has batchim.",
        classification="protected_surface",
    ),
]


LEXICAL_MIDDLE_DOT_EXTENDED_CASES = [
    TextCase(
        case_id="lexical-middle-dot-ai-ml",
        text="AI·ML",
        expected="에이아이 엠엘",
        rule="policy / lexical middle dot boundary matrix",
        reason="An acronym-on-both-sides lexical middle-dot compound must stay on the lexical route rather than a numeric route.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-ml-ai",
        text="ML·AI",
        expected="엠엘 에이아이",
        rule="policy / lexical middle dot boundary matrix",
        reason="Lexical middle-dot compounds must be order-stable across acronym pairs.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-iso-ai",
        text="ISO·AI",
        expected="아이에스오 에이아이",
        rule="policy / lexical middle dot boundary matrix",
        reason="Dictionary and acronym readings must coexist under the lexical middle-dot route.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-ai-kospi",
        text="AI·KOSPI",
        expected="에이아이 코스피",
        rule="policy / lexical middle dot boundary matrix",
        reason="Acronym plus dictionary-listed lexical reading must remain a protected lexical middle-dot output.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-kospi-iec",
        text="KOSPI·IEC",
        expected="코스피 아이이씨",
        rule="policy / lexical middle dot boundary matrix",
        reason="Dictionary-listed lexical reading plus acronym must remain a protected lexical middle-dot output.",
        classification="protected_surface",
    ),
]


SINGLE_LETTER_HYPHEN_EXTENDED_CASES = [
    TextCase(
        case_id="single-letter-hyphen-z-generation",
        text="Z-세대",
        expected="지-세대",
        rule="policy / single-letter hyphen generalized cases",
        reason="Single-letter hyphen lexical compounds must generalize beyond the original K- examples.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-d-day",
        text="D-데이",
        expected="디-데이",
        rule="policy / single-letter hyphen generalized cases",
        reason="Single-letter hyphen lexical compounds must preserve the hyphen and lexical tail for additional safe cases.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-a-match-topic",
        text="A-매치는",
        expected="에이-매치는",
        rule="policy / single-letter hyphen generalized cases",
        reason="The protected hyphen compound must survive normal following particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-c-level-object",
        text="C-레벨을",
        expected="씨-레벨을",
        rule="policy / single-letter hyphen generalized cases",
        reason="The protected hyphen compound must survive normal following particle attachment.",
        classification="protected_surface",
    ),
]


UNICODE_TILDE_EXTENDED_CASES = [
    TextCase(
        case_id="unicode-tilde-unit-kg-math",
        text="3∼8kg",
        expected="삼에서 팔 킬로그램",
        rule="policy / unicode tilde range extended",
        reason="Unicode tilde normalization must work for additional basic units, not just cm.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-unit-kg-fullwidth",
        text="3～8kg",
        expected="삼에서 팔 킬로그램",
        rule="policy / unicode tilde range extended",
        reason="Fullwidth tilde normalization must work for additional basic units, not just cm.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-counter-ascii",
        text="1~3명",
        expected="일에서 세 명",
        rule="policy / unicode tilde range extended",
        reason="Shared-suffix range normalization must remain compatible with counter-noun readings.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-counter-math",
        text="1∼3명",
        expected="일에서 세 명",
        rule="policy / unicode tilde range extended",
        reason="Unicode tilde normalization must remain compatible with counter-noun readings.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-counter-fullwidth",
        text="1～3명",
        expected="일에서 세 명",
        rule="policy / unicode tilde range extended",
        reason="Fullwidth tilde normalization must remain compatible with counter-noun readings.",
        classification="range",
    ),
]


LARGE_UNIT_ATOMIC_PARSE_EXTENDED_CASES = [
    TextCase(
        case_id="large-unit-atomic-1gyeong",
        text="1경",
        expected="일경",
        rule="policy / large-unit atomic parse extended",
        reason="Atomic parse must cover larger documented large-unit suffixes as well.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-10hae",
        text="10해",
        expected="십해",
        rule="policy / large-unit atomic parse extended",
        reason="Atomic parse must cover larger documented large-unit suffixes as well.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-1gyeong-topic",
        text="1경은",
        expected="일경은",
        rule="policy / large-unit atomic parse extended",
        reason="Particle attachment after larger large-unit suffixes must preserve atomic rendering.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-10hae-subject",
        text="10해가",
        expected="십해가",
        rule="policy / large-unit atomic parse extended",
        reason="Particle attachment after larger large-unit suffixes must preserve atomic rendering.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-1000eok-object",
        text="1000억을",
        expected="천억을",
        rule="policy / large-unit atomic parse extended",
        reason="Atomic parse must remain stable under particle attachment for four-digit prefixes.",
        classification="large_unit",
    ),
]


SIGNED_DEGREE_EXTENDED_CASES = [
    TextCase(
        case_id="signed-degree-plain-trailing-zero-decimal",
        text="-12.0도",
        expected="마이너스 십이쩜영도",
        rule="policy / signed degree quantity extended",
        reason="The signed-degree parser must preserve decimal precision when the input explicitly includes a trailing zero.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-plain-zero",
        text="-0도",
        expected="마이너스 영도",
        rule="policy / signed degree quantity extended",
        reason="The signed-degree parser must handle zero without falling back to a raw minus sign surface.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-celsius-integer",
        text="-12℃",
        expected="영하 십이도",
        rule="policy / signed degree quantity extended",
        reason="Temperature-specific negative handling must apply to integer Celsius values as well.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-celsius-zero",
        text="-0℃",
        expected="영하 영도",
        rule="policy / signed degree quantity extended",
        reason="Temperature-specific negative handling must apply to zero Celsius values as well.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-fahrenheit-integer",
        text="-12℉",
        expected="화씨 영하 십이도",
        rule="policy / signed degree quantity extended",
        reason="Temperature-specific negative handling must apply to integer Fahrenheit values as well.",
        classification="signed_degree",
    ),
]


POST_PROCESSING_RESTRICTION_CASES = [
    TextCase(
        case_id="post-processing-restriction-currency-hardcoded-yuro",
        text="유로을",
        expected="유로을",
        rule="policy / post-processing restriction",
        reason="Hangul-only input must bypass legacy post-processing instead of receiving a hardcoded particle rewrite.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-restriction-currency-hardcoded-en",
        text="엔로",
        expected="엔로",
        rule="policy / post-processing restriction",
        reason="Hangul-only input must bypass legacy particle correction.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-restriction-rieul-exception-baereol",
        text="배럴으로",
        expected="배럴으로",
        rule="policy / post-processing restriction",
        reason="Rieul exception correction is removed because Hangul literals are immutable.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-restriction-rieul-exception-al",
        text="알으로",
        expected="알으로",
        rule="policy / post-processing restriction",
        reason="Hangul counters are immutable literals; post-processing must not correct their particles.",
        classification="post_processing",
    ),
]


@pytest.mark.parametrize("case", ACRONYM_PARTICLE_PRESERVATION_CASES, ids=lambda case: case.case_id)
def test_acronym_protected_output_preserves_input_particles(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", ACRONYM_OUTPUT_INTERACTION_CASES, ids=lambda case: case.case_id)
def test_acronym_protected_output_extended_interactions(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", LEXICAL_MIDDLE_DOT_EXTENDED_CASES, ids=lambda case: case.case_id)
def test_lexical_middle_dot_extended_boundary_matrix(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", SINGLE_LETTER_HYPHEN_EXTENDED_CASES, ids=lambda case: case.case_id)
def test_single_letter_hyphen_extended_generalization(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", UNICODE_TILDE_EXTENDED_CASES, ids=lambda case: case.case_id)
def test_unicode_tilde_extended_range_matrix(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", LARGE_UNIT_ATOMIC_PARSE_EXTENDED_CASES, ids=lambda case: case.case_id)
def test_large_unit_atomic_parse_extended_matrix(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", SIGNED_DEGREE_EXTENDED_CASES, ids=lambda case: case.case_id)
def test_signed_degree_extended_matrix(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", POST_PROCESSING_RESTRICTION_CASES, ids=lambda case: case.case_id)
def test_post_processing_restriction_matrix(case: TextCase):
    assert_exact(transform_text(case.text), case)
