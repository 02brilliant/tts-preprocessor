from __future__ import annotations

import pytest

from engine.span_engine import transform


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "설명은 [첫 번째 문장입니다. 두 번째 문장입니다.]입니다",
            "설명은 첫 번째 문장입니다. 두 번째 문장입니다.입니다",
        ),
        ("설명은 (첫 번째 문장입니다. 두 번째 문장입니다.)입니다", "설명은 입니다"),
    ],
)
def test_phase18c_bracket_blockers_keep_no_newline(text: str, expected: str) -> None:
    output = transform(text)

    assert output == expected
    assert "\n" not in output


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "첫 문장입니다. 90km/h입니다. 두 번째 문장입니다.",
            "첫 문장입니다. 시속 구십 킬로미터입니다. 두 번째 문장입니다.",
        ),
        (
            "첫 문장입니다. 123-456-7890입니다. 두 번째 문장입니다.",
            "첫 문장입니다. 일이삼 사오육 칠팔구공입니다. 두 번째 문장입니다.",
        ),
        (
            "첫 문장입니다. 종로3가입니다. 두 번째 문장입니다.",
            "첫 문장입니다. 종로 삼 가입니다. 두 번째 문장입니다.",
        ),
    ],
)
def test_phase18c_generated_surface_blockers_keep_no_newline(
    text: str, expected: str
) -> None:
    output = transform(text)

    assert output == expected
    assert "\n" not in output


@pytest.mark.parametrize(
    "text",
    [
        "첫 문장입니다. http://x/y 를 확인했다. 다음 문장입니다.",
        "첫 문장입니다. path/to/file 을 확인했다. 다음 문장입니다.",
        "첫 문장입니다. code_like_token 을 확인했다. 다음 문장입니다.",
    ],
)
def test_phase18c_url_path_code_like_blockers_keep_no_newline(text: str) -> None:
    output = transform(text)

    assert output == text
    assert "\n" not in output
