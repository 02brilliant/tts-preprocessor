from __future__ import annotations

import json

from engine.span_engine import compare


def test_phase19c_build_default_compare_corpus_contract() -> None:
    build_default_compare_corpus = getattr(compare, "build_default_compare_corpus")
    corpus = build_default_compare_corpus()

    assert isinstance(corpus, list)
    assert len(corpus) >= 15

    ids = [entry.id for entry in corpus]
    texts = [entry.text for entry in corpus]
    assert len(ids) == len(set(ids))
    assert all(isinstance(text, str) and text for text in texts)
    assert all(isinstance(entry.tags, (tuple, list)) for entry in corpus)
    assert all(
        entry.expected_category is None
        or entry.expected_category in compare.COMPARE_CATEGORIES
        for entry in corpus
    )

    for entry in corpus:
        json.dumps(entry.to_dict(), ensure_ascii=False)

    expected_texts = {
        "3~8cm",
        "2025-01-03",
        "90km/h",
        "60fps",
        "종로3가",
        "[3kg]",
        "http://x/90km/h",
        "전문가 유지",
        "123-456-7890",
        "긴급번호 112는",
        "21명",
        "그리고 우리는 결과를 확인했다",
    }
    assert expected_texts.issubset(set(texts))

    all_tags = {tag for entry in corpus for tag in entry.tags}
    expected_tags = {
        "canonical",
        "preserve",
        "bracket",
        "url_path",
        "intended_diff",
        "suspicious_guard",
        "prosody",
        "admin",
        "compound_unit",
        "emergency",
        "date_time",
        "range",
        "counter",
        "hyphen_phone",
    }
    assert expected_tags.issubset(all_tags)


def test_phase19c_default_corpus_tag_policy_is_conservative() -> None:
    build_default_compare_corpus = getattr(compare, "build_default_compare_corpus")
    corpus = build_default_compare_corpus()

    intended_entries = [entry for entry in corpus if "intended_diff" in entry.tags]
    suspicious_entries = [entry for entry in corpus if "suspicious_guard" in entry.tags]

    assert intended_entries
    assert suspicious_entries
    assert all(
        entry.expected_category in {None, "intended_v5_change"}
        for entry in intended_entries
    )

