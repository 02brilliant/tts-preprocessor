import pytest

from engine.pipeline.transform_engine import transform_text
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
        case_id="adversarial-ratio-like-colon-form",
        text="16:9",
        expected="16:9",
        rule="ambiguity guard / ratio-like colon form",
        reason="Ratio-like colon forms are explicitly excluded from time conversion.",
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
        case_id="adversarial-spaced-middle-dot-right",
        text="12· 3",
        expected="12· 3",
        rule="middle dot / spacing guard",
        reason="Whitespace on either side of a middle dot breaks the decimal interpretation.",
    ),
    TextCase(
        case_id="adversarial-ambiguous-year-month-dot-form",
        text="2025.01",
        expected="2025.01",
        rule="decimal vs date ambiguity",
        reason="A short year-month dotted form is explicitly identified as ambiguous and should stay original.",
    ),
    TextCase(
        case_id="adversarial-standalone-2400",
        text="24:00",
        expected="24:00",
        rule="HH:MM / standalone guard",
        reason="Even though 24:00 is a valid boundary time, it still needs positive time context and should stay original when standalone.",
    ),
    TextCase(
        case_id="adversarial-emergency-disallowed-suffix-ho",
        text="119호",
        expected="백십구호",
        rule="emergency number / disallowed suffix",
        reason="호 is not an allowed emergency tail, so the token must fall back to the general number reading.",
    ),
    TextCase(
        case_id="adversarial-emergency-disallowed-suffix-beon",
        text="112번",
        expected="백십이번",
        rule="emergency number / disallowed suffix",
        reason="번 is not an allowed emergency tail, so 112 must normalize as a general number, not an emergency number.",
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
        expected="12-15장",
        rule="hyphen protection / ambiguity guard",
        reason="A two-block numeric hyphen plus Korean suffix remains protected and must not become a range or counter reading.",
    ),
    TextCase(
        case_id="adversarial-generic-two-block-hyphen",
        text="1-2",
        expected="1-2",
        rule="hyphen protection / generic negative",
        reason="The policy explicitly avoids broadly interpreting generic two-block hyphen forms.",
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
    assert_exact(transform_text(case.text), case)
