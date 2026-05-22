from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    "text",
    [
        "USB300",
        "A12.3B",
        "EURA 300",
        "300EURabc",
    ],
)
def test_mixed_alnum_and_currency_contaminated_code_like_tokens_preserve(
    text: str,
) -> None:
    assert transform(text) == text


def test_usb_version_spacing_keeps_existing_behavior() -> None:
    assert transform("USB 3.0") == "유에스비 삼쩜영"
