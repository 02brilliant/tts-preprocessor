from __future__ import annotations

import pytest

from engine.span_engine import transform, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.3 비상계엄", "십이삼 비상계엄"),
        ("12.3 계엄", "십이삼 계엄"),
        ("12.3 사태", "십이삼 사태"),
        ("12.3비상계엄", "십이삼비상계엄"),
        ("그리고, 12.3 비상계엄", "그리고, 십이삼 비상계엄"),
    ],
)
def test_one_digit_right_block_event_now_normalizes(text: str, expected: str) -> None:
    output = transform_with_trace(text)

    # In Phase 28B, this will FAIL because implementation is still preserving
    assert output.normalized_text == expected
    assert any(
        log.owner == "event"
        for log in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('12.12', '십이-쩜-일이'),
        ('4.19', '사-쩜-일구'),
        ('6.25', '육-쩜-이오'),
        ('3.1', '삼-쩜-일'),
        ("12.12가 있었다", "12.12가 있었다"),
        ('12.12 그 사태', '십이-쩜-일이 그 사태'),
        ('12.12은 사태였다', '십이-쩜-일이는 사태였다'),
        ("2025.01.03", "이천이십오년 일월 삼일"),
        ('2025.01', '이천이십오-쩜-영일'),
        ('1.234', '일-쩜-이삼사'),
        ('3.14', '삼-쩜-일사'),
        ("1.2.3", "1.2.3"),  # Multiple dots not handled by decimal
        ("12.12abc", "12.12abc"),
        ('12.12 kg', '십이-쩜-일이-킬로그램'),
    ],
)
def test_ambiguous_or_unsupported_dotted_event_behavior(text: str, expected: str) -> None:
    assert transform(text) == expected


def test_square_bracket_event_is_preserved_with_brackets() -> None:
    output = transform_with_trace("[12.12 사태]")

    assert output.normalized_text == "12.12 사태"
    assert not any(claim.owner == "event" for claim in output.trace.claim_logs)


def test_parenthesized_event_is_finally_elided_without_event_claim() -> None:
    output = transform_with_trace("(12.12 사태)")

    assert output.normalized_text == ""
    assert not any(claim.owner == "event" for claim in output.trace.claim_logs)
