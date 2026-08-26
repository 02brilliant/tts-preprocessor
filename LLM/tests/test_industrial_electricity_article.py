from __future__ import annotations

from pathlib import Path

import pytest

from LLM.invocation_gate import decide_llm_invocation
from LLM.provenance import build_normalization_snapshot
from LLM.response_validation import LLMStageContractError, validate_response
from engine.main import transform_output


ARTICLE_PATH = Path(__file__).parent / "fixtures" / "industrial_electricity_article.txt"


@pytest.fixture(scope="module")
def normalized_article():
    output = transform_output(ARTICLE_PATH.read_text(encoding="utf-8"))
    return output.normalized_text, build_normalization_snapshot(output)


@pytest.mark.parametrize("stage_level", (3, 4, 5))
def test_industrial_electricity_article_invokes_llm(stage_level: int, normalized_article) -> None:
    normalized_text, _snapshot = normalized_article

    assert decide_llm_invocation(normalized_text, stage_level=stage_level).call_llm is True


@pytest.mark.parametrize("prompt_level", (1, 2, 3))
def test_industrial_electricity_article_accepts_safe_llm_output_with_ascii_space(
    prompt_level: int,
    normalized_article,
) -> None:
    normalized_text, snapshot = normalized_article
    # LLMs commonly emit an ordinary space for the source NBSP. This is a
    # formatting-equivalent change, while `2조` is the residual reading work
    # intentionally delegated from the rule engine to the LLM stage.
    speech_text = normalized_text.replace("\u00a0", " ").replace("2조", "이조")

    assert validate_response(
        normalized_text,
        speech_text,
        prompt_level=prompt_level,
        snapshot=snapshot,
    ) == speech_text


@pytest.mark.parametrize("prompt_level", (1, 2, 3))
def test_industrial_electricity_article_marks_unchanged_residual_for_ui(
    prompt_level: int,
    normalized_article,
) -> None:
    normalized_text, snapshot = normalized_article

    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response(
            normalized_text,
            normalized_text,
            prompt_level=prompt_level,
            snapshot=snapshot,
        )

    assert exc_info.value.code == "RESIDUAL_SPEECH_SURFACE"
    assert exc_info.value.severity == "Medium"
    assert normalized_text[
        exc_info.value.output_start : exc_info.value.output_end
    ] == "2"
