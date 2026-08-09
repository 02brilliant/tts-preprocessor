"""This file includes migrated tests from *_cases.py to ensure pytest collection."""

from engine.main import transform


def test_basic_dictionary_matches():
    assert transform("AI") == "에이아이"
    assert transform("KBS") == "케이비에스"
    assert transform("WHO") == "더블유에이치오"
    assert transform("RAM") == "램"


def test_josa_attachment():
    assert transform("AI는") == "에이아이는"
    assert transform("KBS가") == "케이비에스가"
    assert transform("KOSPI는") == "코스피는"


def test_longest_match():
    assert transform("USB 3.0") == "유에스비 삼쩜영"
    assert transform("USB") == "유에스비"


def test_managed_mixed_case_dictionary_text_is_read():
    assert transform("OpenAI") == "오픈 에이아이"
    assert transform("L-SAM") == "엘-샘"
    assert transform("M-SAM") == "엠-샘"
    assert transform("FA") == "에프에이"
    assert transform("MQ") == "엠큐"


def test_uppercase_abbreviation():
    assert transform("CPU") == "씨피유"


def test_mixed_script_dictionary_entries():
    assert transform("5·18 민주화운동") == "오일팔 민주화운동"
    assert transform("12.12 사태") == "십이십이 사태"
    assert transform("Wi-Fi") == "와이파이"


def test_unmatched_lowercase_text_is_preserved():
    assert transform("abc") == "abc"
