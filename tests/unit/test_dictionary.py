"""This file includes migrated tests from *_cases.py to ensure pytest collection."""

from engine.parsers.dictionary_matcher import match_dictionary


def test_basic_dictionary_matches():
    assert match_dictionary("AI") == "에이아이"
    assert match_dictionary("KBS") == "케이비에스"
    assert match_dictionary("WHO") == "더블유에이치오"
    assert match_dictionary("RAM") == "램"


def test_josa_attachment():
    assert match_dictionary("AI는") == "에이아이는"
    assert match_dictionary("KBS가") == "케이비에스가"
    assert match_dictionary("KOSPI는") == "코스피는"


def test_longest_match():
    assert match_dictionary("USB 3.0") == "유에스비 삼쩜영"
    assert match_dictionary("USB") == "유에스비"


def test_no_partial_match():
    assert match_dictionary("OpenAI") == None


def test_uppercase_abbreviation():
    assert match_dictionary("CPU") == "씨피유"


def test_mixed_script_dictionary_entries():
    assert match_dictionary("5·18 민주화운동") == "오일팔 민주화운동"
    assert match_dictionary("12.12 사태") == "십이십이 사태"
    assert match_dictionary("Wi-Fi") == "와이파이"


def test_invalid_input_returns_none():
    assert match_dictionary("abc") == None


def test_dictionary_invalid_input_returns_none():
    assert match_dictionary("abc") == None
