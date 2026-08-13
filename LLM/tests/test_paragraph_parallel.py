from __future__ import annotations

from LLM.paragraph_parallel import join_paragraph_units, split_paragraph_units


def test_single_paragraph_is_not_split() -> None:
    text = "국물은 좋습니다."

    chunks, separators = split_paragraph_units(text)

    assert chunks == (text,)
    assert separators == ()
    assert join_paragraph_units(chunks, separators) == text


def test_double_newline_paragraphs_round_trip() -> None:
    text = "첫째 문단입니다.\n\n둘째 문단입니다."

    chunks, separators = split_paragraph_units(text)

    assert chunks == ("첫째 문단입니다.", "둘째 문단입니다.")
    assert separators == ("\n\n",)
    assert join_paragraph_units(chunks, separators) == text


def test_single_newline_paragraphs_round_trip() -> None:
    text = "첫째 문단입니다.\n둘째 문단입니다."

    chunks, separators = split_paragraph_units(text)

    assert chunks == ("첫째 문단입니다.", "둘째 문단입니다.")
    assert separators == ("\n",)
    assert join_paragraph_units(chunks, separators) == text


def test_mixed_newline_runs_are_preserved() -> None:
    text = "하나.\n\n\n둘.\n셋."

    chunks, separators = split_paragraph_units(text)

    assert chunks == ("하나.", "둘.", "셋.")
    assert separators == ("\n\n\n", "\n")
    assert join_paragraph_units(chunks, separators) == text


def test_code_fence_newlines_are_not_split() -> None:
    text = "설명입니다.\n\n```json\n{\"a\": 1}\n```\n\n다음 문단입니다."

    chunks, separators = split_paragraph_units(text)

    assert chunks == (
        "설명입니다.",
        "```json\n{\"a\": 1}\n```",
        "다음 문단입니다.",
    )
    assert separators == ("\n\n", "\n\n")
    assert join_paragraph_units(chunks, separators) == text


def test_json_object_newlines_are_not_split() -> None:
    text = '앞 문단입니다.\n\n{"path": "/tmp/a.json",\n"value": 1}\n\n뒤 문단입니다.'

    chunks, separators = split_paragraph_units(text)

    assert chunks == (
        "앞 문단입니다.",
        '{"path": "/tmp/a.json",\n"value": 1}',
        "뒤 문단입니다.",
    )
    assert separators == ("\n\n", "\n\n")
    assert join_paragraph_units(chunks, separators) == text
