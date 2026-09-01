import pytest

from engine.main import transform as transform_text
from tests._policy_case import TextCase, assert_exact


REGRESSION_CASES = [
    TextCase(
        case_id="regression-protected-acronym-fta-following-noun",
        text="FTA 요건만 충족하면",
        expected="에프티에이 요건만 충족하면",
        rule="regression / protected acronym output",
        reason="A fallback acronym reading must stay compact and protected before a following lexical noun.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="regression-lexical-middle-dot-ai-semiconductor",
        text="AI·반도체",
        expected="에이아이·반도체",
        rule="regression / lexical middle dot compound",
        reason="The managed lexical side is read while the original middle-dot boundary remains protected.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="regression-lexical-token-non-rewrite-expert",
        text="민관 전문가",
        expected="민관 전문가",
        rule="regression / lexical token non-rewrite",
        reason="Post-processing must not rewrite a plain lexical noun such as 전문가.",
        classification="post_processing",
    ),
    TextCase(
        case_id="regression-lexical-token-non-rewrite-issneun",
        text="키울 수 있는 양날의 칼",
        expected="키울 수 있는 양날의 칼",
        rule="regression / lexical token non-rewrite",
        reason="Post-processing must not rewrite an inflected lexical token such as 있는.",
        classification="post_processing",
    ),
    TextCase(
        case_id="regression-unicode-tilde-shared-suffix-month",
        text="1∼11월",
        expected="일월에서 십일월",
        rule="regression / unicode tilde range",
        reason="Unicode tilde range separators must normalize to the shared-suffix range route.",
        classification="range",
    ),
    TextCase(
        case_id="regression-large-unit-atomic-6402eok-dollar",
        text="6402억 달러",
        expected="육천사백이억 달러",
        rule="regression / atomic large-unit parse",
        reason="A large-unit expression must remain atomic with no stray whitespace before 억.",
        classification="large_unit",
    ),
    TextCase(
        case_id="regression-single-letter-hyphen-k-food",
        text="K-푸드",
        expected="케이푸드",
        rule="regression / single-letter hyphen lexical compound",
        reason="The K-Hangul owner reads K, consumes the lexical hyphen, and preserves the Korean tail.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="regression-single-letter-hyphen-k-beauty",
        text="K-뷰티",
        expected="케이뷰티",
        rule="regression / single-letter hyphen lexical compound",
        reason="The compact K-Hangul owner output must be protected from post-processing rewrites.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="regression-single-letter-hyphen-k-pop",
        text="K-POP",
        expected="케이팝",
        rule="regression / single-letter hyphen lexical compound",
        reason="The managed K-POP dictionary route owns and renders the complete token.",
        classification="protected_surface",
    ),
    TextCase(
        case_id="regression-signed-degree-plain-decimal",
        text="-1.3도",
        expected='마이너스 일-쩜-삼도',
        rule="regression / signed degree quantity",
        reason="Plain signed degree quantities default to 마이너스, not 영하 or a partial minus sign surface.",
        classification="signed_degree",
    ),
    TextCase(
        case_id="regression-signed-degree-plain-decimal-zero",
        text="-0.5도",
        expected='마이너스 영-쩜-오도',
        rule="regression / signed degree quantity",
        reason="Signed degree quantities with leading zero decimals must keep the full spoken minus reading.",
        classification="signed_degree",
    ),
]


@pytest.mark.parametrize("case", REGRESSION_CASES, ids=lambda case: case.case_id)
def test_policy_reinforcement_regressions(case: TextCase):
    assert_exact(transform_text(case.text), case)
