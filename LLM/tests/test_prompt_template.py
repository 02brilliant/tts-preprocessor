from __future__ import annotations

from pathlib import Path

import pytest

from LLM.prompt_template import PromptTemplateError, build_prompt


def test_prompt_replaces_exactly_one_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("앞\n{{TTS_INPUT_TEXT}}\n뒤", encoding="utf-8")

    assert build_prompt("원고", path) == "앞\n원고\n뒤"


@pytest.mark.parametrize(
    "template",
    [
        "자리표시자 없음",
        "{{TTS_INPUT_TEXT}}\n{{TTS_INPUT_TEXT}}",
    ],
)
def test_prompt_rejects_invalid_placeholder_count(
    tmp_path: Path,
    template: str,
) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text(template, encoding="utf-8")

    with pytest.raises(PromptTemplateError, match="exactly one"):
        build_prompt("원고", path)


def test_prompt_reloads_file_for_each_request(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("첫째 {{TTS_INPUT_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "첫째 원고"

    path.write_text("둘째 {{TTS_INPUT_TEXT}}", encoding="utf-8")
    assert build_prompt("원고", path) == "둘째 원고"
