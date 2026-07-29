from __future__ import annotations

import pytest

from LLM.client import LLMResponseError
from LLM.response_validation import LLMStageContractError, validate_response


def test_integrated_response_accepts_pronunciation_and_prosody_changes() -> None:
    source = "국물은 같이 읽고 있습니다."
    output = "궁무른, 가치 일꼬 읻씀니다."

    assert validate_response(source, output) == output


@pytest.mark.parametrize(
    "output",
    (
        "궁무른 가치 일꼬 읻씀니다",
        "궁무른\n가치 일꼬 읻씀니다.",
        "궁무른; 가치 일꼬 읻씀니다.",
        "```궁무른 가치 일꼬 읻씀니다.```",
        "**궁무른 가치 일꼬 읻씀니다.**",
    ),
)
def test_integrated_response_rejects_structure_or_wrapper_changes(
    output: str,
) -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_response("국물은 같이 읽고 있습니다.", output)

    assert exc_info.value.stage == "speech"
    assert exc_info.value.output_text == output
    assert isinstance(exc_info.value, LLMResponseError)


def test_integrated_response_preserves_existing_whitespace_and_punctuation() -> None:
    source = "첫 문장,\n둘째 문장."
    output = "첟 문장, \n둘째 문장."

    assert validate_response(source, output) == output


def test_integrated_response_preserves_lock_tokens_exactly() -> None:
    with pytest.raises(LLMStageContractError, match="locked token") as exc_info:
        validate_response(
            "URL은 <LOCK_0001>입니다.",
            "유아레른 <LOCK_0002>임니다.",
        )

    assert exc_info.value.output_text == "유아레른 <LOCK_0002>임니다."
