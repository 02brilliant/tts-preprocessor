"""Desired preserve contract for numeric_matrix §10.3 file-like open gaps.

Current production partially reads trailing numeric fragments
(file-25..오십.txt). Section 10.3 requires these surfaces to be resolved
(full preserve) before any broad segmented malformed numeric reader expands.

Keep current-state audit in test_malformed_numeric_segmented_reading_policy.py.
This module tracks the desired end state as strict xfail until implemented.
"""

from __future__ import annotations

import pytest

from engine.main import transform


@pytest.mark.xfail(
    strict=True,
    reason=(
        "numeric_matrix §10.3 open follow-up: file-like/code-like surfaces must "
        "fully preserve before segmented malformed numeric expansion"
    ),
)
@pytest.mark.parametrize(
    "text",
    [
        "file-25..50.txt",
        "v25..50",
        "SKU25..50",
    ],
)
def test_file_like_malformed_numeric_desired_full_preserve(text: str) -> None:
    assert transform(text) == text
