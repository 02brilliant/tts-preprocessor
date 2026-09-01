import pytest

from engine.main import transform as transform_text
from tests._policy_case import TextCase, assert_exact


ACRONYM_PROTECTED_OUTPUT_CASES = [
    TextCase(
        case_id="acronym-protected-ai",
        text="AI",
        expected="에이아이",
        rule="policy / acronym protected output",
        reason="Dictionary acronym readings must remain compact protected surfaces.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-fta",
        text="FTA",
        expected="에프티에이",
        rule="policy / acronym protected output",
        reason="Fallback acronym readings must stay compact rather than being re-segmented later.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-mfn",
        text="MFN",
        expected="엠에프엔",
        rule="policy / acronym protected output",
        reason="Fallback acronym results are protected phrases once generated.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-iso",
        text="ISO",
        expected="아이에스오",
        rule="policy / acronym protected output",
        reason="Acronym outputs must remain intact as final surfaces.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-iec",
        text="IEC",
        expected="아이이씨",
        rule="policy / acronym protected output",
        reason="Acronym outputs must remain intact as final surfaces.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-following-noun",
        text="FTA 요건만 충족하면",
        expected="에프티에이 요건만 충족하면",
        rule="policy / acronym protected output",
        reason="A protected acronym output must remain compact before a following lexical noun.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-topic-particle-fta",
        text="FTA는",
        expected="에프티에이는",
        rule="policy / acronym protected output",
        reason="A protected acronym output must keep its compact body while allowing a normal topic-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-subject-particle-fta",
        text="FTA가",
        expected="에프티에이가",
        rule="policy / acronym protected output",
        reason="A protected acronym output must keep its compact body while allowing a normal subject-particle attachment.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-particle-context",
        text="AI가",
        expected="에이아이가",
        rule="policy / acronym protected output",
        reason="Particle contexts may attach after the protected acronym output, but the acronym body itself must not be rewritten.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-topic-particle",
        text="AI는",
        expected="에이아이는",
        rule="policy / acronym protected output",
        reason="Compact acronym output must remain unsplit in particle contexts.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="acronym-protected-topic-particle-mfn",
        text="MFN은",
        expected="엠에프엔은",
        rule="policy / acronym protected output",
        reason="Acronym protected output and normal particle attachment must coexist without internal rewrite.",
        classification="protected_surface",
    ),
]


LEXICAL_TOKEN_NON_REWRITE_CASES = [
    TextCase(
        case_id="lexical-non-rewrite-expert",
        text="전문가",
        expected="전문가",
        rule="policy / lexical token non-rewrite",
        reason="A plain lexical noun must not be rewritten by particle or batchim correction.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-gukga",
        text="국가",
        expected="국가",
        rule="policy / lexical token non-rewrite",
        reason="A plain lexical noun must not be rewritten by particle or batchim correction.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-issneun",
        text="있는",
        expected="있는",
        rule="policy / lexical token non-rewrite",
        reason="An inflected lexical token must remain untouched by post-processing.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-anneun",
        text="않는",
        expected="않는",
        rule="policy / lexical token non-rewrite",
        reason="An inflected lexical token must remain untouched by post-processing.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-uiui",
        text="의의",
        expected="의의",
        rule="policy / lexical token non-rewrite",
        reason="A lexical surface with ambiguous vowels must not be broad-rewritten.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-aiga",
        text="아이가",
        expected="아이가",
        rule="policy / lexical token non-rewrite",
        reason="A general lexical token must not be mistaken for an acronym-derived particle repair target.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-eiga",
        text="에이가",
        expected="에이가",
        rule="policy / lexical token non-rewrite",
        reason="A general lexical token must not be mistaken for an acronym-derived particle repair target.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-sentence-expert",
        text="민관 전문가",
        expected="민관 전문가",
        rule="policy / lexical token non-rewrite",
        reason="Lexical nouns inside a sentence must remain unchanged by post-processing.",
        classification="post_processing",
    ),
    TextCase(
        case_id="lexical-non-rewrite-sentence-issneun",
        text="키울 수 있는 양날의 칼",
        expected="키울 수 있는 양날의 칼",
        rule="policy / lexical token non-rewrite",
        reason="Inflected lexical tokens inside a sentence must remain unchanged by post-processing.",
        classification="post_processing",
    ),
]


LEXICAL_MIDDLE_DOT_COMPOUND_CASES = [
    TextCase(
        case_id="lexical-middle-dot-ai-semiconductor",
        text="AI·반도체",
        expected="에이아이·반도체",
        rule="policy / lexical middle dot compound",
        reason="A managed lexical side is read while the middle dot and Korean literal remain preserved.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-ai-standard",
        text="AI·표준",
        expected="에이아이·표준",
        rule="policy / lexical middle dot compound",
        reason="The managed acronym is read while the lexical middle dot remains in the canonical output.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-iso-iec",
        text="ISO·IEC",
        expected="아이에스오·아이이씨",
        rule="policy / lexical middle dot compound",
        reason="Managed acronym readings keep the original lexical middle-dot boundary.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="lexical-middle-dot-kospi-ai",
        text="KOSPI·AI",
        expected="코스피·에이아이",
        rule="policy / lexical middle dot compound",
        reason="Dictionary readings may change both sides without deleting the lexical middle dot.",
        classification="protected_surface",
    ),
]


SINGLE_LETTER_HYPHEN_LEXICAL_CASES = [
    TextCase(
        case_id="single-letter-hyphen-k-food",
        text="K-푸드",
        expected="케이푸드",
        rule="policy / single-letter hyphen lexical compound",
        reason="The K-Hangul owner reads K, consumes the lexical hyphen, and preserves the Korean tail.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-k-beauty",
        text="K-뷰티",
        expected="케이뷰티",
        rule="policy / single-letter hyphen lexical compound",
        reason="The K-Hangul owner produces a compact protected reading for the complete token.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-k-pop",
        text="K-POP",
        expected="케이팝",
        rule="policy / single-letter hyphen lexical compound",
        reason="The managed K-POP dictionary route owns and renders the complete token.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-b-plan",
        text="B-플랜",
        expected="B-플랜",
        rule="policy / non-K single-letter hyphen preserve",
        reason="The compact lexical owner is K-specific, so an unsupported B-prefix token remains original.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-a-match",
        text="A-매치",
        expected="A-매치",
        rule="policy / non-K single-letter hyphen preserve",
        reason="The compact lexical owner is K-specific, so an unsupported A-prefix token remains original.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="single-letter-hyphen-c-level",
        text="C-레벨",
        expected="C-레벨",
        rule="policy / non-K single-letter hyphen preserve",
        reason="The compact lexical owner is K-specific, so an unsupported C-prefix token remains original.",
        classification="protected_surface",
    ),
]


UNICODE_TILDE_RANGE_CASES = [
    TextCase(
        case_id="unicode-tilde-month-ascii",
        text="1~11월",
        expected="일월에서 십일월",
        rule="policy / unicode tilde range",
        reason="ASCII tilde shared-suffix ranges remain the reference behavior.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-month-math",
        text="1∼11월",
        expected="일월에서 십일월",
        rule="policy / unicode tilde range",
        reason="Mathematical tilde must normalize to the same range behavior as ASCII tilde.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-month-fullwidth",
        text="1～11월",
        expected="일월에서 십일월",
        rule="policy / unicode tilde range",
        reason="Fullwidth tilde must normalize to the same range behavior as ASCII tilde.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-unit-ascii",
        text="3~8cm",
        expected="삼에서 팔-센티미터",
        rule="policy / unicode tilde range",
        reason="ASCII tilde numeric-unit ranges remain the reference behavior.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-unit-math",
        text="3∼8cm",
        expected="삼에서 팔-센티미터",
        rule="policy / unicode tilde range",
        reason="Mathematical tilde must normalize before numeric-unit range parsing.",
        classification="range",
    ),
    TextCase(
        case_id="unicode-tilde-unit-fullwidth",
        text="3～8cm",
        expected="삼에서 팔-센티미터",
        rule="policy / unicode tilde range",
        reason="Fullwidth tilde must normalize before numeric-unit range parsing.",
        classification="range",
    ),
]


LARGE_UNIT_ATOMIC_PARSE_CASES = [
    TextCase(
        case_id="large-unit-atomic-1eok",
        text="1억",
        expected="일억",
        rule="policy / large-unit atomic parse",
        reason="Leading one before 억 is part of the atomic numeric reading.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-10eok",
        text="10억",
        expected="십억",
        rule="policy / large-unit atomic parse",
        reason="Atomic parse must handle smaller large-unit readings without introducing repair spacing.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-6402eok",
        text="6402억",
        expected="육천사백이억",
        rule="policy / large-unit atomic parse",
        reason="A large-unit suffix must be rendered atomically with no repair whitespace.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-1jo",
        text="1조",
        expected="일조",
        rule="policy / large-unit atomic parse",
        reason="Leading one before 조 is part of the atomic numeric reading.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-100eok",
        text="100억",
        expected="백억",
        rule="policy / large-unit atomic parse",
        reason="Atomic parse must read the full number with the large-unit suffix attached.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-1000eok",
        text="1000억",
        expected="천억",
        rule="policy / large-unit atomic parse",
        reason="Atomic parse must preserve compact large-unit rendering across four-digit prefixes.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-1200jo",
        text="1200조",
        expected="천이백조",
        rule="policy / large-unit atomic parse",
        reason="Large-unit readings must not insert stray whitespace before the suffix.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-6402eok-eul",
        text="6402억을",
        expected="육천사백이억을",
        rule="policy / large-unit atomic parse",
        reason="Particle attachment after an atomic large-unit reading must not decompose the suffix boundary.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-1jo-ga",
        text="1조가",
        expected="1조가",
        rule="policy / contextual number-unit defer",
        reason="A particle-attached 조 without a financial or group anchor remains source-exact.",
        classification="contextual_defer",
    ),
    TextCase(
        case_id="large-unit-atomic-100eok-eun",
        text="100억은",
        expected="백억은",
        rule="policy / large-unit atomic parse",
        reason="Particle attachment after 억 must preserve the atomic large-unit reading.",
        classification="large_unit",
    ),
    TextCase(
        case_id="large-unit-atomic-6402eok-dollar",
        text="6402억 달러",
        expected="육천사백이억 달러",
        rule="policy / large-unit atomic parse",
        reason="Atomic large-unit readings must stay intact before a following noun.",
        classification="large_unit",
    ),
]


SIGNED_DEGREE_QUANTITY_CASES = [
    TextCase(
        case_id="signed-degree-plain-decimal",
        text="-1.3도",
        expected='마이너스 일-쩜-삼도',
        rule="policy / signed degree quantity",
        reason="Plain signed degree quantities use 마이너스 by default.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-plain-decimal-zero",
        text="-0.5도",
        expected='마이너스 영-쩜-오도',
        rule="policy / signed degree quantity",
        reason="Plain signed degree quantities keep the explicit minus reading even with a zero integer part.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-plain-integer",
        text="-12도",
        expected="마이너스 십이도",
        rule="policy / signed degree quantity",
        reason="Plain signed integer degree quantities use the same dedicated route.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-celsius",
        text="-1.3℃",
        expected='영하 일-쩜-삼도',
        rule="policy / signed degree quantity",
        reason="Temperature-specific negative readings still use 영하 for Celsius.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="signed-degree-fahrenheit",
        text="-0.5℉",
        expected='화씨 영하 영-쩜-오도',
        rule="policy / signed degree quantity",
        reason="Temperature-specific negative readings still use 화씨 영하 for Fahrenheit.",
        classification="signed_degree",
    ),
]


POST_PROCESSING_WHITELIST_ONLY_CASES = [
    TextCase(
        case_id="post-processing-whitelist-lexical-noun",
        text="전문가",
        expected="전문가",
        rule="policy / post-processing whitelist only",
        reason="A lexical noun is outside the whitelist and must not be rewritten.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-whitelist-inflected-form",
        text="있는",
        expected="있는",
        rule="policy / post-processing whitelist only",
        reason="An inflected lexical form is outside the whitelist and must not be rewritten.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-whitelist-acronym-output",
        text="FTA 요건만 충족하면",
        expected="에프티에이 요건만 충족하면",
        rule="policy / post-processing whitelist only",
        reason="Protected acronym output must not be broken by later post-processing.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-whitelist-lexical-middle-dot",
        text="AI·반도체",
        expected="에이아이·반도체",
        rule="policy / post-processing whitelist only",
        reason="A protected lexical middle-dot surface is outside the post-processing rewrite whitelist.",
        classification="post_processing",
    ),
    TextCase(
        case_id="post-processing-whitelist-single-letter-hyphen",
        text="K-푸드",
        expected="케이푸드",
        rule="policy / post-processing whitelist only",
        reason="The K-Hangul owner output is final and must not be rewritten by post-processing.",
        classification="post_processing",
    ),
]


@pytest.mark.parametrize("case", ACRONYM_PROTECTED_OUTPUT_CASES, ids=lambda case: case.case_id)
def test_acronym_protected_output(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", LEXICAL_TOKEN_NON_REWRITE_CASES, ids=lambda case: case.case_id)
def test_lexical_token_non_rewrite(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", LEXICAL_MIDDLE_DOT_COMPOUND_CASES, ids=lambda case: case.case_id)
def test_lexical_middle_dot_compound(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", SINGLE_LETTER_HYPHEN_LEXICAL_CASES, ids=lambda case: case.case_id)
def test_single_letter_hyphen_lexical_compound(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", UNICODE_TILDE_RANGE_CASES, ids=lambda case: case.case_id)
def test_unicode_tilde_range(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", LARGE_UNIT_ATOMIC_PARSE_CASES, ids=lambda case: case.case_id)
def test_large_unit_atomic_parse(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", SIGNED_DEGREE_QUANTITY_CASES, ids=lambda case: case.case_id)
def test_signed_degree_quantity(case: TextCase):
    assert_exact(transform_text(case.text), case)


@pytest.mark.parametrize("case", POST_PROCESSING_WHITELIST_ONLY_CASES, ids=lambda case: case.case_id)
def test_post_processing_whitelist_only(case: TextCase):
    assert_exact(transform_text(case.text), case)
