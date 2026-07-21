from __future__ import annotations

import pytest

from engine.main import transform


def production_source_transform(text: str) -> str:
    return transform(text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1", "일"),
        ("+1", "플러스 일"),
        ("-1", "마이너스 일"),
        ("1000", "천"),
        ("1,000", "천"),
        ("+1,000", "플러스 천"),
        ("-1,000", "마이너스 천"),
        ("1.5", "일쩜오"),
        ("+1.5", "플러스 일쩜오"),
        ("-1.5", "마이너스 일쩜오"),
        ("0.05", "영쩜영오"),
        ("+0.05", "플러스 영쩜영오"),
        ("-0.05", "마이너스 영쩜영오"),
        ("25.50", "이십오쩜오영"),
        ("+25.50", "플러스 이십오쩜오영"),
        ("-25.50", "마이너스 이십오쩜오영"),
        ("1,000.50", "천쩜오영"),
        ("+1,000.50", "플러스 천쩜오영"),
        ("-2,500.75", "마이너스 이천오백쩜칠오"),
    ],
)
def test_common_standalone_numeric_current_matrix(text: str, expected: str):
    assert production_source_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01", "01"),
        ("+01", "+01"),
        ("-01", "-01"),
        ("01.5", "01.5"),
        ("+01.5", "+01.5"),
        ("-01.5", "-01.5"),
        ("1,00", "1,00"),
        ("1,00.5", "1,00.5"),
        ("+1,00.5", "+1,00.5"),
        ("+.5", "+.5"),
        ("-.5", "-.5"),
        ("1.", "일."),
        ("+1.", "+1."),
        ("3..140", "3..140"),
        ("1,0000", "1,0000"),
    ],
)
def test_common_standalone_malformed_numeric_current_matrix(text: str, expected: str):
    assert production_source_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1kg", "일 킬로그램"),
        ("1.5kg", "일쩜오 킬로그램"),
        ("1,000kg", "천 킬로그램"),
        ("25.50%", "이십오쩜오영 퍼센트"),
        ("1/2%p", "이분의 일 퍼센트포인트"),
        ("KRW25.50", "이십오쩜오영 원"),
        ("USD 25.50", "이십오쩜오영 달러"),
        ("1,000원", "천 원"),
        ("25.50원", "이십오쩜오영 원"),
        ("+25℃", "영상 이십오도"),
        ("25.50℃", "이십오쩜오영도"),
        ("+25.50℃", "영상 이십오쩜오영도"),
        ("1~2테스트", "일에서 이 테스트"),
        ("1.50~2.50테스트", "일쩜오영에서 이쩜오영 테스트"),
        ("3:4테스트", "삼 대 사 테스트"),
        ("3:4.50테스트", "삼 대 사쩜오영 테스트"),
        ("1-2kg", "일에서 이 킬로그램"),
        ("010-1234-5678", "공일공 일이삼사 오육칠팔"),
        ("2천8백28억", "이천팔백이십팔억"),
        ("25.50억", "이십오쩜오영 억"),
    ],
)
def test_owner_attached_numeric_current_matrix(text: str, expected: str):
    assert production_source_transform(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "01kg",
        "1,00kg",
        "+.5kg",
        "1.kg",
        "+.5%p",
        "1,00원",
        "USD 1,00",
        "+.5℃",
        "1~~2테스트",
        "1~",
        "3::4테스트",
        "1-2테스트",
        "1-2",
        "+1.5-2kg",
        "-1.5-2kg",
        "2,34억",
        "2,,345억",
        "25..50억",
        "3백..4십만",
    ],
)
def test_owner_attached_invalid_surfaces_preserve_without_partial_fallback(text: str):
    assert production_source_transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("`KRW1000`", "`KRW1000`"),
        ('{"price":"KRW1000"}', '{"price":"KRW1000"}'),
        ("/path/2,345억/log", "/path/2,345억/log"),
        ("https://example.com?q=KRW1000", "https://example.com?q=KRW1000"),
        ("v3백4십만", "v3백4십만"),
        ("case 3:4테스트", "case 3:4테스트"),
    ],
)
def test_protected_contexts_precede_numeric_owners(text: str, expected: str):
    assert production_source_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("09:30", "구시 삼십분"),
        ("13:05 브리핑", "십삼시 오분 브리핑"),
        ("3:4", "삼 대 사"),
        ("1-2kg", "일에서 이 킬로그램"),
        ("1-2", "1-2"),
        ("1234-5678", "일이삼사 오육칠팔"),
        ("001-23-456", "공공일 이삼 사오육"),
    ],
)
def test_time_like_and_hyphen_exception_matrix(text: str, expected: str):
    assert production_source_transform(text) == expected
