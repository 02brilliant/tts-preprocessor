from __future__ import annotations

import pytest

from engine.main import transform
from engine.span_engine import transform_with_trace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("274번지", "이백칠십사-번지"),
        ("5 번지", "오-번지"),
        ("5번길", "오-번길"),
        ("5번선", "오-번선"),
        ("100번대", "백-번대"),
        ("5번가", "오-번가"),
        ("시민로5번길", "시민로 오-번길"),
        ("역삼동 12번지", "역삼동 십이-번지"),
        ("종로3가", "종로 삼-가"),
    ],
)
def test_fixed_identifier_and_administrative_suffix_spacing(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "5번길abc",
        "A5번길",
        "01번길",
        "5번길안내",
        "시민로5번길안내",
        "5번지구",
    ],
)
def test_fixed_beon_suffix_unsafe_surface_preserves(text: str) -> None:
    assert transform(text) == text


def test_fixed_beon_suffix_claim_excludes_following_particle() -> None:
    output = transform_with_trace("5번길은")

    assert output.normalized_text == "오-번길은"
    assert [(log.owner, log.span.start, log.span.end) for log in output.trace.claim_logs] == [
        ("contextual_number_unit", 0, 3)
    ]
    assert output.render_pieces[-1].text == "은"
    assert output.render_pieces[-1].provenance == "ORIGINAL_KOREAN"
