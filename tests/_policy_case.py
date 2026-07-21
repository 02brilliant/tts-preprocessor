from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextCase:
    case_id: str
    text: str
    expected: str
    rule: str
    reason: str
    classification: str = ""


def assert_exact(actual: str, case: TextCase) -> None:
    message = (
        (f"classification={case.classification}\n" if case.classification else "")
        + f"{case.rule}: {case.reason}\n"
        + f"input={case.text!r}\n"
        + f"expected={case.expected!r}\n"
        + f"actual={actual!r}"
    )
    assert actual == case.expected, message


def assert_text_exact(actual: str, text: str, expected: str) -> None:
    assert actual == expected, (
        f"input={text!r}\nexpected={expected!r}\nactual={actual!r}"
    )
