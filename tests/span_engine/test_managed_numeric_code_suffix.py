from __future__ import annotations

from pathlib import Path

import pytest

from engine.main import transform
from engine.span_engine import transform_with_trace
from engine.span_engine.lexicon import DICTIONARY_READINGS


MANAGED_NUMERIC_CODE_SOURCE = Path("engine/span_engine/managed_numeric_code.py")


def prod(src: str) -> str:
    result = transform(src)
    return getattr(result, "normalized_text", result)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("GPT4", "지피티 포"),
        ("GPT-4", "지피티-포"),
        ("FA-9", "에프에이-나인"),
        ("FA-50", "에프에이-오십"),
        ("FA-1.5", "에프에이-일쩜오"),
        ("MQ-9", "엠큐-나인"),
        ("MQ-10", "엠큐-십"),
        ("F/A-9", "에프에이-나인"),
        ("f/a-50", "에프에이-오십"),
        ("A/S-1.5", "에이에스-일쩜오"),
        ("mig-9", "미그-나인"),
        ("Mig-21", "미그-이십일"),
        ("Su-57", "수호이-오십칠"),
        ("Su-27", "수호이-이십칠"),
        ("sU-9", "수호이-나인"),
        ("mk-10", "엠케이-십"),
        ("KC-9", "케이씨-나인"),
        ("aim-50", "에이아이엠-오십"),
        ("AGM-1.5", "에이지엠-일쩜오"),
        ("GPT1.5", "지피티 일쩜오"),
        ("GPT-1.5", "지피티-일쩜오"),
        ("KTX1", "케이티엑스 원"),
        ("KTX-1", "케이티엑스-원"),
        ("KBS1", "케이비에스 원"),
        ("KBS-1", "케이비에스-원"),
        ("NASA1", "나사 원"),
        ("NASA-1", "나사-원"),
        ("GUI2", "지유아이 투"),
        ("GUI-2", "지유아이-투"),
        ("YAML2", "야믈 투"),
        ("YAML-2", "야믈-투"),
        ("REST1", "레스트 원"),
        ("REST-1", "레스트-원"),
        ("RAM2", "램 투"),
        ("RAM-2", "램-투"),
        ("ROM3", "롬 쓰리"),
        ("ROM-3", "롬-쓰리"),
        ("OAuth2", "오어스 투"),
        ("OAuth-2", "오어스-투"),
        ("WAN1", "더블유에이엔 원"),
        ("WAN-1", "더블유에이엔-원"),
        ("WLAN2", "더블유랜 투"),
        ("WLAN-2", "더블유랜-투"),
        ("Wi-Fi6", "와이파이 식스"),
        ("Wi-Fi-6", "와이파이-식스"),
        ("version1.5", "버전 일쩜오"),
        ("version-1.5", "버전-일쩜오"),
        ("release1.5", "릴리즈 일쩜오"),
        ("release-1.5", "릴리즈-일쩜오"),
        ("API2", "에이피아이 투"),
        ("JSON2", "제이슨 투"),
        ("HDMI2", "에이치디엠아이 투"),
    ],
)
def test_managed_dictionary_numeric_code_suffix_positive(src: str, expected: str) -> None:
    assert prod(src) == expected
    output = transform_with_trace(src)
    assert any(
        claim.owner == "managed_acronym_numeric_code"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("F/A-9", "에프에이-나인"),
        ("f/a-9", "에프에이-나인"),
        ("F/A9", "에프에이 나인"),
        ("A/S-9", "에이에스-나인"),
        ("a/s-9", "에이에스-나인"),
        ("A/S9", "에이에스 나인"),
        ("MIG-9", "미그-나인"),
        ("mig-9", "미그-나인"),
        ("Mig9", "미그 나인"),
        ("SU-9", "수호이-나인"),
        ("su-9", "수호이-나인"),
        ("Su9", "수호이 나인"),
        ("MK-9", "엠케이-나인"),
        ("mk-9", "엠케이-나인"),
        ("Mk9", "엠케이 나인"),
        ("KC-9", "케이씨-나인"),
        ("kc-9", "케이씨-나인"),
        ("Kc9", "케이씨 나인"),
        ("AIM-9", "에이아이엠-나인"),
        ("aim-9", "에이아이엠-나인"),
        ("Aim9", "에이아이엠 나인"),
        ("AGM-9", "에이지엠-나인"),
        ("agm-9", "에이지엠-나인"),
        ("Agm9", "에이지엠 나인"),
    ],
)
def test_case_insensitive_numeric_only_managed_bases(src: str, expected: str) -> None:
    assert prod(src) == expected


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("GPT", "지피티"),
        ("version", "버전"),
        ("release", "릴리즈"),
        ("GPT는", "지피티는"),
        ("version은", "버전은"),
        ("release가", "릴리즈가"),
    ],
)
def test_new_managed_dictionary_standalone_entries(src: str, expected: str) -> None:
    assert prod(src) == expected


@pytest.mark.parametrize("src", ["Su", "su", "sU"])
def test_su_without_numeric_suffix_remains_unmanaged(src: str) -> None:
    assert prod(src) == src


@pytest.mark.parametrize("src", ["Mig", "mig", "MiG"])
def test_mig_without_numeric_suffix_remains_unmanaged(src: str) -> None:
    assert prod(src) == src


def test_managed_dictionary_numeric_code_is_registry_backed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(DICTIONARY_READINGS, "ZZZ", "지지지")

    assert prod("ZZZ-2") == "지지지-투"
    output = transform_with_trace("ZZZ-2")
    assert any(
        claim.owner == "managed_acronym_numeric_code"
        for claim in output.trace.claim_logs
    )


def test_managed_numeric_code_source_has_no_owner_local_base_allowlist() -> None:
    source = MANAGED_NUMERIC_CODE_SOURCE.read_text(encoding="utf-8")

    assert "_MANAGED_NUMERIC_CODE_BASES" not in source
    assert "_PRESERVED_FOUR_DIGIT_BASES" not in source


@pytest.mark.parametrize(
    "src",
    [
        "GPT+4",
        "GPT-+4",
        "GPT--4",
        "GPT+1.5",
        "GPT-+1.5",
        "version-+1.5",
        "release--1.5",
        "version-01.5",
        "version-.5",
        "version-1.",
        "KTX-2024",
        "GPT-2024",
        "version-2024",
        "release-2024",
    ],
)
def test_managed_dictionary_numeric_code_rejects_signed_or_malformed(src: str) -> None:
    assert prod(src) == src


@pytest.mark.parametrize(
    "src",
    [
        "abc1.5",
        "abc-1.5",
        "build25",
        "build-25",
        "file25",
        "file-25",
        "foo2",
        "foo-2",
    ],
)
def test_unregistered_ascii_word_numeric_suffix_preserves(src: str) -> None:
    assert prod(src) == src


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("AI", "에이아이"),
        ("CPU", "씨피유"),
        ("USB", "유에스비"),
        ("AI가", "에이아이가"),
        ("CPU는", "씨피유는"),
        ("USB를", "유에스비를"),
        ("AI3", "AI3"),
        ("CPU900", "CPU900"),
        ("USB300", "USB300"),
    ],
)
def test_fallback_covered_acronyms_are_not_managed_numeric_code_bases(
    src: str, expected: str
) -> None:
    assert prod(src) == expected
    output = transform_with_trace(src)
    assert not any(
        claim.owner == "managed_acronym_numeric_code"
        for claim in output.trace.claim_logs
    )


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("/path/GPT-4/log", "/path/GPT-4/log"),
        ("https://example.com/GPT-4", "https://example.com/GPT-4"),
        ("`GPT-4`", "`GPT-4`"),
        ("[GPT-4]", "GPT-4"),
        ('{"value":"GPT-4"}', '{"value":"GPT-4"}'),
        ("/path/version-1.5/log", "/path/version-1.5/log"),
        ("https://example.com/version-1.5", "https://example.com/version-1.5"),
        ("`version-1.5`", "`version-1.5`"),
        ("[version-1.5]", "version-1.5"),
        ('{"value":"version-1.5"}', '{"value":"version-1.5"}'),
        ("file-GPT-4.txt", "file-GPT-4.txt"),
        ("GPT-4abc", "GPT-4abc"),
        ("GPT4abc", "GPT4abc"),
        ("https://example.com/A/S-1.5", "https://example.com/A/S-1.5"),
        ("/path/A/S-1.5/log", "/path/A/S-1.5/log"),
        ("version-1.5.txt", "version-1.5.txt"),
        ("release-1.5.json", "release-1.5.json"),
    ],
)
def test_managed_dictionary_numeric_code_protected_or_unsafe_preserves(
    src: str, expected: str
) -> None:
    assert prod(src) == expected
