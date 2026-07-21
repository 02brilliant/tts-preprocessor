import pytest

from engine.main import transform
from tests._policy_case import TextCase, assert_exact


LEADING_ONE_CASES = [
    # Policy: leading 1 is suppressed for 십/백/천/만 and retained for 억/조/경.
    TextCase(
        case_id="leading-one-10",
        text="10",
        expected="십",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 십.",
    ),
    TextCase(
        case_id="leading-one-100",
        text="100",
        expected="백",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 백.",
    ),
    TextCase(
        case_id="leading-one-1000",
        text="1000",
        expected="천",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 천.",
    ),
    TextCase(
        case_id="leading-one-10000",
        text="10000",
        expected="만",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 만.",
    ),
    TextCase(
        case_id="leading-one-100000",
        text="100000",
        expected="십만",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 십만.",
    ),
    TextCase(
        case_id="leading-one-1000000",
        text="1000000",
        expected="백만",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 백만.",
    ),
    TextCase(
        case_id="leading-one-10000000",
        text="10000000",
        expected="천만",
        rule="leading 1 rule / suppress family",
        reason="The leading 1 is suppressed for 천만.",
    ),
    TextCase(
        case_id="leading-one-100000000",
        text="100000000",
        expected="일억",
        rule="leading 1 rule / retain family",
        reason="The leading 1 must be retained for 억.",
    ),
    TextCase(
        case_id="leading-one-1000000000000",
        text="1000000000000",
        expected="일조",
        rule="leading 1 rule / retain family",
        reason="The leading 1 must be retained for 조.",
    ),
    TextCase(
        case_id="leading-one-10000000000000000",
        text="10000000000000000",
        expected="일경",
        rule="leading 1 rule / retain family",
        reason="The leading 1 must be retained for 경.",
    ),
    TextCase(
        case_id="leading-one-100000000000000000000",
        text="100000000000000000000",
        expected="100000000000000000000",
        rule="large-number width / unsupported 해 group preserve",
        reason="The canonical ordinary number reader ends at 경; an unsupported 21-digit no-Hangul input preserves exactly.",
        classification="canonical",
    ),
]


NUMERIC_SCALING_CASES = [
    # Policy: large-number reading and scaling must share the same leading-1 rule.
    TextCase(
        case_id="scaling-large-integer",
        text="1234567890123",
        expected="일조 이천삼백사십오억 육천칠백팔십구만 백이십삼",
        rule="numeric scaling / large integer",
        reason="Large integers must segment by Korean large units while preserving the documented leading-1 behavior.",
    ),
    TextCase(
        case_id="scaling-large-comma-decimal",
        text="1,234,567,890,123.456",
        expected="일조이천삼백사십오억육천칠백팔십구만백이십삼쩜사오육",
        rule="numeric scaling / canonical compact large decimal",
        reason="The decimal owner validates comma grouping atomically and uses the compact ordinary integer reader before exact fractional digits.",
        classification="canonical",
    ),
    TextCase(
        case_id="scaling-compact-krw-decimal",
        text="1.5조 원",
        expected="일쩜오 조 원",
        rule="numeric scaling / compact KRW",
        reason="Compact decimal big-unit currency keeps the decimal reading instead of expanding into lower large-number units.",
    ),
]


@pytest.mark.parametrize("case", LEADING_ONE_CASES, ids=lambda case: case.case_id)
def test_leading_one_policy(case: TextCase):
    # The docs define two families: suppressed leading-1 units and retained leading-1 high units.
    assert_exact(transform(case.text), case)


@pytest.mark.parametrize("case", NUMERIC_SCALING_CASES, ids=lambda case: case.case_id)
def test_numeric_scaling_policy(case: TextCase):
    # Numeric scaling must stay consistent with the core number-reading policy.
    assert_exact(transform(case.text), case)
