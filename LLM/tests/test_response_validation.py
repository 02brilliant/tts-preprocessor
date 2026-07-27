from __future__ import annotations

import pytest

from LLM.client import LLMResponseError
from LLM.response_validation import (
    LLMStageContractError,
    validate_prosody_response,
    validate_speech_response,
)


def test_prosody_accepts_only_inserted_commas_and_ascii_spaces() -> None:
    source = "정부는 발표하고 다음 달 시행합니다."
    output = "정부는 발표하고, 다음 달 시행합니다."

    assert validate_prosody_response(source, output) == output


@pytest.mark.parametrize(
    "output",
    (
        "정부는 바꾸고 다음 달 시행합니다.",
        "정부는 발표하고 다음 달 시행합니다",
        "정부는 발표하고\n다음 달 시행합니다.",
    ),
)
def test_prosody_rejects_rewrite_delete_or_newline(output: str) -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_prosody_response(
            "정부는 발표하고 다음 달 시행합니다.",
            output,
        )

    assert exc_info.value.stage == "prosody"
    assert exc_info.value.output_text == output
    assert isinstance(exc_info.value, LLMResponseError)


def test_speech_accepts_pronunciation_changes_with_fixed_structure() -> None:
    source = "국물은, 같이 읽고 있습니다."
    output = "궁무른, 가치 일꼬 읻씀니다."

    assert validate_speech_response(source, output) == output


@pytest.mark.parametrize(
    "output",
    (
        "궁무른 가치 일꼬 읻씀니다.",
        "궁무른, 가치  일꼬 읻씀니다.",
        "```궁무른, 가치 일꼬 읻씀니다.```",
        "**궁무른, 가치 일꼬 읻씀니다.**",
    ),
)
def test_speech_rejects_structure_or_wrapper_changes(output: str) -> None:
    with pytest.raises(LLMStageContractError) as exc_info:
        validate_speech_response("국물은, 같이 읽고 있습니다.", output)

    assert exc_info.value.stage == "speech"
    assert exc_info.value.output_text == output


def test_speech_preserves_lock_tokens_exactly() -> None:
    with pytest.raises(LLMStageContractError, match="locked token") as exc_info:
        validate_speech_response(
            "URL은 <LOCK_0001>입니다.",
            "유아레른 <LOCK_0002>임니다.",
        )

    assert exc_info.value.output_text == "유아레른 <LOCK_0002>임니다."
