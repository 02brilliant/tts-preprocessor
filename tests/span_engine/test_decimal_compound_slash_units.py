from __future__ import annotations

import pytest

from engine.main import transform


def _production_transform(text: str) -> str:
    result = transform(text)
    normalized = getattr(result, "normalized_text", result)
    assert isinstance(normalized, str)
    return normalized


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("90km/h", "시속 구십 킬로미터"),
        ("5.6km/h", "시속 오쩜육 킬로미터"),
        ("7.8m/s", "초속 칠쩜팔 미터"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("3.2mg/L", "리터당 삼쩜이 밀리그램"),
        ("3.2g/L", "리터당 삼쩜이 그램"),
        ("120.5mg/dL", "데시리터당 백이십쩜오 밀리그램"),
        ("12.5MB/s", "초당 십이쩜오 메가바이트"),
        ("4.5cm/s", "초속 사쩜오 센티미터"),
        ("6.7km/s", "초속 육쩜칠 킬로미터"),
    ],
)
def test_decimal_numeric_core_uses_registered_compound_template(
    source: str, expected: str
) -> None:
    assert _production_transform(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("90km/h", "시속 구십 킬로미터"),
        ("5m/s", "초속 오 미터"),
        ("15.2km/L", "리터당 십오쩜이 킬로미터"),
        ("5㎎／L", "리터당 오 밀리그램"),
        ("3.2㎎／L", "리터당 삼쩜이 밀리그램"),
        ("12.5MB／s", "초당 십이쩜오 메가바이트"),
    ],
)
def test_existing_integer_decimal_and_alias_templates_remain_authoritative(
    source: str, expected: str
) -> None:
    assert _production_transform(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        ".5km/h",
        "01.5km/h",
        "1.km/h",
        "1..5km/h",
        "1,00.5km/h",
        "3.2mg/La",
        "3.2㎎／La",
        "3.2foo/bar",
    ],
)
def test_malformed_or_unregistered_slash_surfaces_preserve(source: str) -> None:
    assert _production_transform(source) == source


@pytest.mark.parametrize(
    "source",
    [
        "1/3",
        "2026/06/01",
        "/path/5.6km/h/log",
        "https://example.com/5.6km/h",
        "A / B",
        "5.6km / h",
        "`5.6km/h`",
        "[5.6km/h]",
    ],
)
def test_slash_conflicts_and_protected_contexts_are_preserved_or_owned(
    source: str,
) -> None:
    expected = {
        "1/3": "삼분의 일",
        "2026/06/01": "이천이십육년 유월 일일",
        "[5.6km/h]": "5.6km/h",
    }.get(source, source)
    assert _production_transform(source) == expected
