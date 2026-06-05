from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "90㎞ / h",
        "3m / sec",
        "60 fps",
        "10 Mbps",
        "9 dBi",
        "-10MB/s",
        "+10MB/s",
        "010MB/s",
        "60fpsabc",
        "10Mbpskg",
        "3000rpm.html",
        "http://x/10MB/s",
        "https://x/60fps",
        "/10MB/s",
        "path/10MB/s",
        "10MB/s/path",
        "10MB/s.html",
    ],
)
def test_phase17b_compound_inventory_preserve(text: str) -> None:
    assert transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90 km/hr", "시속 구십 킬로미터"),
        ("3 m/s", "초속 삼 미터"),
        ("10 KB/s", "초당 십 킬로바이트"),
        ("100 MB/s", "초당 백 메가바이트"),
        ("2 g/L", "리터당 이 그램"),
        ("120 mg/L", "리터당 백이십 밀리그램"),
    ],
)
def test_phase36b_one_space_compound_inventory_now_transforms(
    text: str, expected: str
) -> None:
    assert transform(text) == expected


def test_phase36b_comma_data_rate_compound_unit_now_transforms() -> None:
    assert transform("1,000KB/s") == "초당 천 킬로바이트"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3.5km/h", "시속 삼쩜오 킬로미터"),
        ("120.5mg/dL", "데시리터당 백이십쩜오 밀리그램"),
    ],
)
def test_decimal_registered_compound_inventory_now_transforms(
    text: str, expected: str
) -> None:
    assert transform(text) == expected
