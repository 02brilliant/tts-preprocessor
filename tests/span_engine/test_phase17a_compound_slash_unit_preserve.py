from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "90km / h",
        "90 km / h",
        "-90km/h",
        "+90km/h",
        "090km/h",
        "90km/habc",
        "90km/hkg",
        "90km//h",
        "90km/",
        "90/km",
        "km/h",
        "MB/s",
        "http://x/90km/h",
        "https://x/90km/h",
        "/90km/h",
        "path/90km/h",
        "90km/h/path",
        "90km/h.html",
    ],
)
def test_compound_slash_unit_preserve_and_forbidden(text: str) -> None:
    assert transform(text) == text


def test_decimal_compound_slash_unit_now_transforms() -> None:
    assert transform("3.5km/h") == "시속 삼쩜오 킬로미터"


def test_phase36b_one_space_compound_slash_unit_now_transforms() -> None:
    assert transform("90 km/h") == "시속 구십 킬로미터"


def test_phase36b_comma_compound_slash_unit_now_transforms() -> None:
    assert transform("1,000km/h") == "시속 천 킬로미터"


@pytest.mark.parametrize(
    ("text", "forbidden"),
    [
        ("http://x/90km/h", "http://x/시속 구십 킬로미터"),
        ("90km/habc", "시속 구십 킬로미터abc"),
        ("90km/h.html", "시속 구십 킬로미터.html"),
    ],
)
def test_compound_slash_unit_forbidden_partial_outputs(
    text: str, forbidden: str
) -> None:
    assert transform(text) != forbidden
