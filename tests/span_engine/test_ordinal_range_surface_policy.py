from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine import SourceSpan, transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1~3번째", "첫-번째에서 세-번째"),
        ("1∼3번째", "첫-번째에서 세-번째"),
        ("2~12번째", "두-번째에서 열두-번째"),
        ("39~40번째", "서른아홉-번째에서 사십-번째"),
        ('1~2.5번째', '첫-번째에서 이-쩜-오-번째'),
        ("1~3번째만", "첫-번째에서 세-번째만"),
        ("1~3째", "첫째에서 셋째"),
        ("1∼3째", "첫째에서 셋째"),
        ("2~12째", "둘째에서 열두째"),
        ("39~40째", "서른아홉째에서 사십째"),
        ("1~3째만", "첫째에서 셋째만"),
    ],
)
def test_ordinal_range_reads_both_endpoints(text: str, expected: str) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "0~3번째",
        "01~3번째",
        "1~03번째",
        "0~3째",
        "01~3째",
        "1~03째",
        "1~2.5째",
        "제1~3번째",
        "제 1~3번째",
        "제1~3째",
        "제 1~3째",
        "A1~3째",
    ],
)
def test_invalid_or_prefixed_ordinal_range_preserves_atomically(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "generated", "suffix_span", "tail"),
    [
        ("1~3번째만", "첫-번째에서 세-", SourceSpan(3, 5), "만"),
        ("1~3째만", "첫째에서 셋", SourceSpan(3, 4), "만"),
    ],
)
def test_ordinal_range_claims_numeric_core_and_preserves_suffix_and_tail(
    text: str, generated: str, suffix_span: SourceSpan, tail: str
) -> None:
    output = transform_with_trace(text)

    assert output.trace.claim_logs[0].owner == "range"
    assert output.trace.claim_logs[0].reason == "range_ordinal_suffix_gate"
    assert output.trace.claim_logs[0].span == SourceSpan(0, 3)
    assert output.render_pieces[0].text == generated
    assert output.render_pieces[0].provenance == "GENERATED_READING"
    assert output.render_pieces[1].text == text[suffix_span.start : suffix_span.end]
    assert output.render_pieces[1].source_span == suffix_span
    assert output.render_pieces[1].provenance == "ORIGINAL_KOREAN"
    assert output.render_pieces[-1].text == tail
    assert output.render_pieces[-1].provenance == "ORIGINAL_KOREAN"
