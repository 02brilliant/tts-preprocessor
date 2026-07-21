from __future__ import annotations

import re

from engine.dictionary.base_dictionary import match_dictionary
from engine.dictionary.base_dictionary import PHONE_DIGIT_KO
from engine.parsers.numeric_date_parsers import read_decimal_ko, read_integer_ko


def _read_phone_chunk(text: str) -> str:
    return "".join(PHONE_DIGIT_KO[digit] for digit in text)


def try_parse_phone(text: str) -> str | None:
    if re.fullmatch(r"010-\d{4}-\d{4}", text):
        first, second, third = text.split("-")
        return f"{_read_phone_chunk(first)} {_read_phone_chunk(second)} {_read_phone_chunk(third)}"

    if re.fullmatch(r"02-\d{3}-\d{4}", text):
        first, second, third = text.split("-")
        return f"{_read_phone_chunk(first)} {_read_phone_chunk(second)} {_read_phone_chunk(third)}"

    if re.fullmatch(r"\d{4}-\d{4}", text):
        first, second = text.split("-")
        return f"{_read_phone_chunk(first)} {_read_phone_chunk(second)}"

    return None


def try_parse_ph(text: str) -> str | None:
    match = re.fullmatch(r"pH\s*(\d+(?:\.\d+)?)", text)
    if not match:
        return None

    number_text = match.group(1)
    if "." in number_text:
        return f"피에이치 {read_decimal_ko(number_text)}"
    return f"피에이치 {read_integer_ko(number_text)}"


def try_parse_upper_decimal_compound(text: str) -> str | None:
    match = re.fullmatch(r"([A-Z]+)\s+(\d+\.\d+)", text)
    if not match:
        return None

    prefix_text, number_text = match.groups()
    prefix_reading = match_dictionary(prefix_text)
    if prefix_reading is None:
        return None

    return f"{prefix_reading} {read_decimal_ko(number_text)}"


def try_parse_angle(text: str) -> str | None:
    match = re.fullmatch(r"(\d+)°", text)
    if not match:
        return None

    return f"{read_integer_ko(match.group(1))}도"
