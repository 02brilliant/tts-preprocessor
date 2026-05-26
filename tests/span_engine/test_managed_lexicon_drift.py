from __future__ import annotations

from pathlib import Path

import pytest

from engine.main import transform_with_rollout
from engine.span_engine import transform_with_trace
from engine.span_engine.lexicon import DICTIONARY_READINGS

MANAGED_DICTIONARY_POLICY = Path("docs/policies/TTS_Preprocessor_managed_dictionary.md")


def production_transform(text: str) -> str:
    return transform_with_rollout(text, mode="span_default", include_debug=False)


def _managed_dictionary_current_entries() -> dict[str, str]:
    text = MANAGED_DICTIONARY_POLICY.read_text(encoding="utf-8")
    current_section = text.split("## 6. Current Managed Dictionary Entries", 1)[1].split(
        "## 7.", 1
    )[0]
    entries: dict[str, str] = {}
    for line in current_section.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3 or cells[2] != "current":
            continue
        entries[cells[0].strip("`")] = cells[1]
    return entries


def test_current_managed_dictionary_inventory_is_span_lexicon() -> None:
    # Adding or changing a current managed dictionary entry requires updating
    # the policy inventory and this parity coverage in the same change.
    current_entries = _managed_dictionary_current_entries()

    assert current_entries["DOCX"] == "디오씨엑스"
    assert current_entries["WiFi"] == "와이파이"
    assert current_entries["3G/4G/5G"] == "쓰리지/포지/파이브지"
    assert current_entries["GraphQL"] == "그래프큐엘"
    for surface, expected in current_entries.items():
        assert DICTIONARY_READINGS[surface] == expected
        assert production_transform(f"{surface} 항목") == f"{expected} 항목"
        trace = transform_with_trace(f"{surface} 항목").trace
        assert any(claim.owner == "dictionary" for claim in trace.claim_logs)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("NASDAQ 지수", "나스닥 지수"),
        ("S&P 지수", "에스앤피 지수"),
        ("S&P500 지수", "에스앤피 오백 지수"),
        ("S&P 500 지수", "에스앤피 오백 지수"),
        (
            "미국 NASDAQ 지수와 S&P500 지수는 오늘 사상 최고가를 경신했다.",
            "미국 나스닥 지수와 에스앤피 오백 지수는 오늘 사상 최고가를 경신했다.",
        ),
        ("NASDAQ100 지수", "나스닥 백 지수"),
        ("NASDAQ 100 지수", "나스닥 백 지수"),
        ("KOSPI200 지수", "코스피 이백 지수"),
        ("KOSPI 200 지수", "코스피 이백 지수"),
        ("KOSDAQ150 지수", "코스닥 백오십 지수"),
        ("KOSDAQ 150 지수", "코스닥 백오십 지수"),
    ],
)
def test_finance_managed_lexicon_and_numeric_suffix(text: str, expected: str) -> None:
    assert production_transform(text) == expected


def test_finance_index_numeric_suffix_full_claim_blocks_partial_p500() -> None:
    output = transform_with_trace("S&P500 지수")

    assert output.normalized_text == "에스앤피 오백 지수"
    assert any(
        claim.owner == "finance_index" and claim.span.start == 0 and claim.span.end == 6
        for claim in output.trace.claim_logs
    )
    assert not any(claim.owner == "single_letter_alnum_code" for claim in output.trace.claim_logs)
    assert "S&피 오백" not in output.normalized_text


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("TTS", "티티에스"),
        ("API", "에이피아이"),
        ("JSON", "제이슨"),
        ("CPU", "씨피유"),
        ("GPU", "지피유"),
        ("GUI", "지유아이"),
        ("Wi-Fi", "와이파이"),
        ("USB", "유에스비"),
        ("PDF", "피디에프"),
        ("OECD", "오이씨디"),
        ("WHO", "더블유에이치오"),
        ("FOMC", "에프오엠씨"),
        ("NASDAQ", "나스닥"),
        ("S&P", "에스앤피"),
        ("KOSPI", "코스피"),
        ("KOSDAQ", "코스닥"),
    ],
)
def test_managed_lexicon_representative_entries_are_span_dictionary(
    surface: str, expected: str
) -> None:
    assert DICTIONARY_READINGS[surface] == expected
    assert production_transform(f"{surface} 항목") == f"{expected} 항목"
    trace = transform_with_trace(f"{surface} 항목").trace
    assert any(claim.owner == "dictionary" for claim in trace.claim_logs)


@pytest.mark.parametrize("text", ["USB300", "APIv2", "A12.3B", "OpenAI"])
def test_managed_lexicon_does_not_expand_broad_fallbacks(text: str) -> None:
    assert production_transform(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("GUI 화면", "지유아이 화면"),
        ("Wi-Fi 연결", "와이파이 연결"),
        ("AI 기술", "에이아이 기술"),
        ("API 문서", "에이피아이 문서"),
        ("TTS 엔진", "티티에스 엔진"),
        ("JSON 파일", "제이슨 파일"),
        ("CPU 사용률", "씨피유 사용률"),
        ("GPU 서버", "지피유 서버"),
        ("USB 포트", "유에스비 포트"),
        ("PDF 문서", "피디에프 문서"),
        ("OECD 보고서", "오이씨디 보고서"),
        ("WHO 발표", "더블유에이치오 발표"),
        ("FOMC 회의", "에프오엠씨 회의"),
        ("KOSPI 지수", "코스피 지수"),
        ("KOSDAQ 시장", "코스닥 시장"),
        ("NASDAQ 지수", "나스닥 지수"),
        ("S&P 지수", "에스앤피 지수"),
        ("DOCX 파일", "디오씨엑스 파일"),
        ("WIFI 연결", "와이파이 연결"),
        ("WiFi 연결", "와이파이 연결"),
        ("2G 서비스", "투지 서비스"),
        ("3G 서비스", "쓰리지 서비스"),
        ("4G 서비스", "포지 서비스"),
        ("5G 서비스", "파이브지 서비스"),
        ("6G 서비스", "식스지 서비스"),
        ("3G/4G/5G 서비스", "쓰리지/포지/파이브지 서비스"),
        ("UI/UX 개선", "유아이 유엑스 개선"),
        ("UX/UI 개선", "유엑스 유아이 개선"),
        ("B2B 거래", "비투비 거래"),
        ("B2C 거래", "비투씨 거래"),
        ("B2B/B2C 전략", "비투비 비투씨 전략"),
        ("OAuth 인증", "오어스 인증"),
        ("WAN 구성", "더블유에이엔 구성"),
        ("WLAN 연결", "더블유랜 연결"),
        ("8K 영상", "에잇케이 영상"),
        ("SDK 문서", "에스디케이 문서"),
        ("CLI 도구", "씨엘아이 도구"),
        ("FAQ 문서", "에프에이큐 문서"),
        ("Q&A 세션", "큐앤에이 세션"),
        ("OS 업데이트", "오에스 업데이트"),
        ("DB 서버", "디비 서버"),
        ("DBMS 설정", "디비엠에스 설정"),
        ("IDE 환경", "아이디이 환경"),
        ("HTTP 요청", "에이치티티피 요청"),
        ("HTTPS 연결", "에이치티티피에스 연결"),
        ("TCP 패킷", "티씨피 패킷"),
        ("UDP 패킷", "유디피 패킷"),
        ("NFC 결제", "엔에프씨 결제"),
        ("UWB 통신", "유더블유비 통신"),
        ("LAN 포트", "랜 포트"),
        ("DOC 파일", "디오씨 파일"),
        ("PPT 자료", "피피티 자료"),
        ("XLS 파일", "엑스엘에스 파일"),
        ("TXT 파일", "티엑스티 파일"),
        ("TSV 데이터", "티에스브이 데이터"),
        ("HWP 문서", "에이치더블유피 문서"),
        ("NoSQL 데이터베이스", "노에스큐엘 데이터베이스"),
        ("GraphQL API", "그래프큐엘 에이피아이"),
        ("gRPC 서버", "지알피씨 서버"),
        ("PCIe 슬롯", "피씨아이이 슬롯"),
        ("JWT 토큰", "제이더블유티 토큰"),
        ("SSL 인증서", "에스에스엘 인증서"),
        ("TLS 연결", "티엘에스 연결"),
        ("SSH 접속", "에스에스에이치 접속"),
        ("DOW 지수", "다우 지수"),
        ("ETF 상품", "이티에프 상품"),
        ("ETN 상품", "이티엔 상품"),
        ("IPO 일정", "아이피오 일정"),
        ("ROE 지표", "알오이 지표"),
        ("PER 지표", "피이알 지표"),
        ("PBR 지표", "피비알 지표"),
        ("EPS 지표", "이피에스 지표"),
        ("BPS 지표", "비피에스 지표"),
        ("YoY 성장률", "와이오와이 성장률"),
        ("MoM 변화", "엠오엠 변화"),
        ("QoQ 실적", "큐오큐 실적"),
        ("Fed 발표", "연준 발표"),
        ("ECB 회의", "이씨비 회의"),
        ("BOJ 결정", "비오제이 결정"),
        ("BOK 기준금리", "비오케이 기준금리"),
        ("IAEA 보고서", "아이에이이에이 보고서"),
        ("FAO 지표", "에프에이오 지표"),
        ("OPEC 회의", "오펙 회의"),
        ("ASEAN 정상회의", "아세안 정상회의"),
        ("IOC 발표", "아이오씨 발표"),
        ("FIFA 랭킹", "피파 랭킹"),
        ("AFC 경기", "에이에프씨 경기"),
        ("KBO 리그", "케이비오 리그"),
        ("KBL 경기", "케이비엘 경기"),
        ("KFA 발표", "케이에프에이 발표"),
        ("MLB 경기", "엠엘비 경기"),
        ("NBA 경기", "엔비에이 경기"),
        ("NFL 경기", "엔에프엘 경기"),
        ("NHL 경기", "엔에이치엘 경기"),
    ],
)
def test_required_current_managed_dictionary_examples(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/path/S&P500/log", "/path/S&P500/log"),
        ("https://example.com?q=S&P500", "https://example.com?q=S&P500"),
        ('{"index":"S&P500"}', '{"index":"S&P500"}'),
        ("`S&P500`", "`S&P500`"),
        ("[S&P500]", "S&P500"),
    ],
)
def test_finance_index_numeric_suffix_respects_protected_contexts(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/path/GUI/log", "/path/GUI/log"),
        ("https://example.com?q=Wi-Fi", "https://example.com?q=Wi-Fi"),
        ('{"term":"GUI"}', '{"term":"GUI"}'),
        ('{"term":"Wi-Fi"}', '{"term":"Wi-Fi"}'),
        ("`GUI`", "`GUI`"),
        ("`Wi-Fi`", "`Wi-Fi`"),
        ("[GUI]", "GUI"),
        ("[Wi-Fi]", "Wi-Fi"),
        ("5GHz 대역", "오 기가헤르츠 대역"),
        ("USB300", "USB300"),
        ("APIv2", "APIv2"),
        ("JSONPath", "JSONPath"),
        ("A12.3B", "A12.3B"),
        ("/path/5G/log", "/path/5G/log"),
        ("https://example.com?q=5G", "https://example.com?q=5G"),
        ('{"term":"5G"}', '{"term":"5G"}'),
        ("`5G`", "`5G`"),
        ("[5G]", "5G"),
        ("/path/WiFi/log", "/path/WiFi/log"),
        ("https://example.com?q=WiFi", "https://example.com?q=WiFi"),
        ('{"term":"WiFi"}', '{"term":"WiFi"}'),
        ("`WiFi`", "`WiFi`"),
        ("[WiFi]", "WiFi"),
    ],
)
def test_current_managed_dictionary_respects_protected_contexts(
    text: str, expected: str
) -> None:
    assert production_transform(text) == expected


@pytest.mark.parametrize(
    "surface",
    [
        "SNP500",
        "JSONPath",
        "5GHz",
    ],
)
def test_non_current_or_owner_specific_examples_are_not_current_inventory(
    surface: str,
) -> None:
    assert surface not in _managed_dictionary_current_entries()
