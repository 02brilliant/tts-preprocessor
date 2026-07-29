import pytest

from engine.main import transform
from tests._policy_case import TextCase, assert_exact


ADVERSARIAL_CASES = [
    # Ambiguity-first behavior: if the docs do not license a transform, the surface should stay original.
    TextCase(
        case_id="adversarial-standalone-hhmm",
        text="12:30",
        expected="12:30",
        rule="ambiguity guard / standalone HH:MM",
        reason="A standalone HH:MM pattern is explicitly ambiguous and must remain original.",
    ),
    TextCase(
        case_id="canonical-bare-colon-semantic-pair",
        text="16:9",
        expected="십육 대 구",
        rule="colon semantic pair / broad non-time-like gate",
        reason="A valid bare N:M surface that is not a strong clock belongs to the semantic-pair owner.",
        classification="override",
    ),
    TextCase(
        case_id="adversarial-bare-decimal-without-event-keyword",
        text="12.3",
        expected="십이쩜삼",
        rule="decimal / disambiguated positive",
        reason="A standard contiguous decimal that lacks event or date context should still convert even in an adversarial matrix.",
    ),
    TextCase(
        case_id="adversarial-currency-invalid-tail",
        text="300USDabc",
        expected="300USDabc",
        rule="partial-match guard / currency",
        reason="Invalid alphabetic tails must block atomic currency parsing completely.",
    ),
    TextCase(
        case_id="adversarial-compound-unit-invalid-tail",
        text="km/Labc",
        expected="km/Labc",
        rule="partial-match guard / compound unit",
        reason="An invalid tail on a slash unit without a numeric prefix must stay original rather than leaking a partial unit rewrite.",
    ),
    TextCase(
        case_id="adversarial-unsupported-currency-per-unit-mix",
        text="€1,234.56/km",
        expected="€1,234.56/km",
        rule="unsupported mixed format / currency + slash unit",
        reason="The policy does not define a currency-per-unit form here, so ambiguity-first handling should keep the original text.",
    ),
    TextCase(
        case_id="adversarial-unsupported-nested-unit",
        text="3.14kg/m²",
        expected="3.14kg/m²",
        rule="unsupported mixed format / nested unit",
        reason="A nested slash-and-exponent unit outside the exact whitelist must skip as a whole.",
    ),
    TextCase(
        case_id="adversarial-spaced-decimal-left",
        text="12 .3",
        expected="12 .3",
        rule="decimal / spacing guard",
        reason="Whitespace around the dot breaks decimal contiguity and must block conversion.",
    ),
    TextCase(
        case_id="canonical-asymmetric-spaced-middle-dot-operands",
        text="12· 3",
        expected="십이· 삼",
        rule="spaced middle dot / independent operands",
        reason="A right-side gap disables contiguous middle-dot parsing; both numeric operands normalize independently while the source separator and gap remain exact.",
        classification="middle_dot",
    ),
    TextCase(
        case_id="canonical-shape-only-year-month-dot-form-is-decimal",
        text="2025.01",
        expected="이천이십오쩜영일",
        rule="decimal / no shape-only date inference",
        reason="A four-digit first block alone is not an explicit Korean date context gate.",
    ),
    TextCase(
        case_id="canonical-standalone-2400-boundary",
        text="24:00",
        expected="이십사시",
        rule="HH:MM / exact standalone day boundary",
        reason="The exact 24:00 boundary is a canonical strong standalone time and overrides the broad ambiguity guard.",
    ),
    TextCase(
        case_id="adversarial-emergency-disallowed-suffix-ho",
        text="119호",
        expected="119호",
        rule="contextual number-unit / deferred identifier",
        reason="호 is not an allowed emergency tail and has no identifier anchor, so the complete surface is deferred.",
    ),
    TextCase(
        case_id="adversarial-emergency-disallowed-suffix-beon",
        text="112번",
        expected="112번",
        rule="contextual number-unit / deferred identifier",
        reason="번 is not an allowed emergency tail and has no identifier or occurrence anchor, so the complete surface is deferred.",
    ),
    TextCase(
        case_id="adversarial-embedded-emergency-token",
        text="긴급번호 A112는 테스트다",
        expected="긴급번호 A112는 테스트다",
        rule="emergency number / boundary guard",
        reason="Emergency context is not enough when the numeric surface is embedded inside a larger token.",
    ),
    TextCase(
        case_id="adversarial-protected-two-block-hyphen",
        text="12-15장",
        expected="십이에서 십오 장",
        rule="hyphen range / canonical registered 장 suffix",
        reason="The registered 장 suffix licenses the restricted hyphen range owner; generic two-block hyphens remain protected.",
        classification="canonical",
    ),
    TextCase(
        case_id="adversarial-ambiguous-compact-hyphen",
        text="1-2",
        expected="1-2",
        rule="ambiguous compact numeric hyphen / preserve",
        reason="A bare compact N-N surface is ambiguous and remains atomic preserve.",
    ),
    TextCase(
        case_id="adversarial-no-numeric-prefix-unit",
        text="m/L",
        expected="m/L",
        rule="compound unit / prefix guard",
        reason="Compound units require a numeric prefix and must remain original without one.",
    ),
    TextCase(
        case_id="adversarial-frequency-invalid-tail",
        text="5Hzabc",
        expected="5Hzabc",
        rule="partial-match guard / frequency",
        reason="The frequency parser must skip invalid tails instead of converting only the numeric-unit prefix.",
    ),
    TextCase(
        case_id="adversarial-ph-invalid-tail",
        text="pH7.4test",
        expected="pH7.4test",
        rule="partial-match guard / pH",
        reason="The pH parser must reject invalid tails with no partial rewrite.",
    ),
    TextCase(
        case_id="adversarial-decimal-alpha-tail",
        text="12.12abc",
        expected="12.12abc",
        rule="decimal / boundary guard",
        reason="A decimal-like surface with an invalid trailing alphabetic tail should not leak a partial decimal conversion.",
    ),
]


@pytest.mark.parametrize("case", ADVERSARIAL_CASES, ids=lambda case: case.case_id)
def test_adversarial_guard_and_ambiguity_matrix(case: TextCase):
    # Adversarial cases deliberately probe boundary mismatches, unsupported mixes, and partial-match hazards.
    assert_exact(transform(case.text), case)
