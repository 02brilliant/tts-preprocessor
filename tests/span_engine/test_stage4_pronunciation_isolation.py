from __future__ import annotations

import pytest

from LLM.pronunciation_lexicon import entries_for_stage
from engine.main import transform, transform_simplified


@pytest.mark.parametrize(
    "surface",
    tuple(entry.surface for entry in entries_for_stage(4) if not entry.contextual),
)
def test_stage4_pronunciation_registry_does_not_change_rule_profiles(surface: str) -> None:
    text = f"{surface}은 확인했습니다."
    assert transform(text) == text
    assert transform_simplified(text) == text
