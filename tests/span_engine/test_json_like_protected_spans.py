from __future__ import annotations

import pytest

from engine.main import transform_with_rollout
from engine.pipeline.transform_engine import transform_text
from engine.span_engine.transform import transform


JSON_LIKE_PROTECTED_CASES = [
    '{"unit":"+1.5 kg"}',
    '{"percent":"+25 %"}',
    '{"price":"KRW1000"}',
    '{"price":"1,000원"}',
    '{"price":"USD 1,000"}',
    '{"temp":"+25℃"}',
    '{"range":"1~2테스트"}',
    '{"ratio":"3:4테스트"}',
    '{"large":"2천8백28억"}',
    '{"large":"2,345억"}',
    '{"hyphen":"1-2kg"}',
]


def production_source_transform(text: str) -> str:
    return transform_with_rollout(text, mode="span_default", include_debug=False)


@pytest.mark.parametrize("text", JSON_LIKE_PROTECTED_CASES)
def test_json_like_string_values_preserve_source_and_production(text: str):
    assert transform(text) == text
    assert production_source_transform(text) == text


@pytest.mark.parametrize("text", JSON_LIKE_PROTECTED_CASES)
def test_json_like_string_values_preserve_legacy_helper_path(text: str):
    assert transform_text(text) == text


def test_json_like_outside_text_still_transforms():
    text = '{"price":"KRW1000"} 밖의 KRW1000'
    expected = '{"price":"KRW1000"} 밖의 천 원'

    assert transform(text) == expected
    assert production_source_transform(text) == expected
    assert transform_text(text) == expected


def test_json_like_integrated_protected_contexts_source_and_production():
    text = (
        "보호 구간에는 `KRW1000`, `2천8백28억`, "
        '{"price":"1,000원"}, {"range":"1~2테스트"}, '
        "/path/2,345억/log, https://example.com?q=KRW1000이 있고, "
        "문장 밖의 KRW1000, 2천8백28억, 1~2테스트는 처리되어야 한다."
    )
    expected = (
        "보호 구간에는 `KRW1000`, `2천8백28억`, "
        '{"price":"1,000원"}, {"range":"1~2테스트"}, '
        "/path/2,345억/log, https://example.com?q=KRW1000이 있고, "
        "문장 밖의 천 원, 이천팔백이십팔억, 일에서 이 테스트는 처리되어야 한다."
    )

    assert transform(text) == expected
    assert production_source_transform(text) == expected


def test_non_json_quote_policy_is_not_expanded():
    text = '그는 "KRW1000"이라고 말했다.'
    expected = '그는 "천 원"이라고 말했다.'

    assert transform(text) == expected
    assert production_source_transform(text) == expected
    assert transform_text(text) == expected
