from __future__ import annotations

import pytest

from engine.main import transform
from tests._policy_case import TextCase, assert_exact


AMBIGUOUS_POLICY_CASES = (
    TextCase(
        case_id="decimal-bare-dotted-short-form",
        text="12.12",
        expected='십이-쩜-일이',
        rule="decimal / bare two-block dotted form",
        reason="event gate가 실패한 유효 bare two-block dotted surface는 ordinary decimal이다.",
        classification="override",
    ),
    TextCase(
        case_id="decimal-shape-only-year-month-form",
        text="2025.01",
        expected='이천이십오-쩜-영일',
        rule="decimal / no shape-only year-month inference",
        reason="4자리.2자리 shape만으로 date preserve owner가 선점하지 않는다.",
        classification="override",
    ),
    TextCase(
        case_id="preserve-unsupported-dotted-chain",
        text="12.12.1990",
        expected="12.12.1990",
        rule="preserve / unsupported dotted chain",
        reason="unsupported dotted chain은 partial consume 없이 preserve 해야 한다.",
        classification="preserve",
    ),
    TextCase(
        case_id="canonical-one-digit-right-strong-dotted-event",
        text="12.3 비상계엄",
        expected="십이삼 비상계엄",
        rule="event / strong immediate keyword",
        reason="A one-digit right block is valid for EVENT_SURFACE when the immediate strong 비상계엄 keyword passes the event gate.",
        classification="override",
    ),
    TextCase(
        case_id="preserve-ph-trailing-contamination",
        text="pH 7.4a",
        expected="pH 7.4a",
        rule="preserve / pH trailing contamination",
        reason="trailing contamination이 있으면 pH parser는 preserve 해야 한다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-invalid-unit-alpha-tail",
        text="5Hzabc",
        expected="5Hzabc",
        rule="preserve / invalid alphabetic tail",
        reason="invalid alphabetic tail은 full-consume 실패로 preserve 해야 한다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-standalone-compound-unit",
        text="m/L",
        expected="m/L",
        rule="preserve / standalone numeric-required compound unit",
        reason="numeric prefix 없는 standalone compound unit은 preserve 대상이다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-invalid-slash-tail",
        text="15.2km/La",
        expected="15.2km/La",
        rule="preserve / invalid slash tail",
        reason="invalid slash tail은 partial consume 없이 preserve 해야 한다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-unsupported-slash-compound",
        text="3km/speed",
        expected="3km/speed",
        rule="preserve / unsupported slash compound",
        reason="unsupported slash compound는 owner parser가 없으므로 preserve 해야 한다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-single-letter-prefixed-hyphen-multiblock",
        text="A-1-2",
        expected="A-1-2",
        rule="preserve / single-letter prefixed hyphen multiblock",
        reason="single-letter-prefixed hyphen multi-block은 normalize entry preserve 대상이다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-scientific-notation-lower",
        text="1e6",
        expected="1e6",
        rule="preserve / unsupported scientific notation",
        reason="scientific notation parser가 없으므로 preserve 해야 한다.",
        classification="preserve",
    ),
    TextCase(
        case_id="preserve-scientific-notation-upper",
        text="3.2E-4",
        expected="3.2E-4",
        rule="preserve / unsupported scientific notation",
        reason="scientific notation parser가 없으므로 preserve 해야 한다.",
        classification="preserve",
    ),
)


@pytest.mark.parametrize("case", AMBIGUOUS_POLICY_CASES, ids=lambda case: case.case_id)
def test_policy_ambiguous_routing_cases(case: TextCase):
    assert_exact(transform(case.text), case)
