from engine.span_engine.transform import transform


def test_multiline_english_quote_preserves_inside_but_transforms_outside():
    text = (
        '연구진은 "The temperature is 25℃.\n'
        "pH 7.4 was maintained for 3 hours.\n"
        'The ratio is 1/3."라고 적었고, '
        "실제 온도 25℃와 pH 7.4, 1/3은 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "The temperature is 25℃.\n" in out
    assert "pH 7.4 was maintained for 3 hours.\n" in out
    assert "The ratio is 1/3." in out
    assert "이십오도" in out
    assert "피에이치 칠쩜사" in out
    assert "삼분의 일" in out
    assert "라고 적었고" in out


def test_multiline_smart_quote_preserves_inside_but_transforms_outside():
    text = (
        "보고서는 “The temperature is 25℃.\n"
        "Result: pH 7.4 was maintained for 3 hours.”라고 설명했고, "
        "본문의 25℃와 $25.99는 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "The temperature is 25℃.\n" in out
    assert "Result: pH 7.4 was maintained for 3 hours." in out
    assert "이십오도" in out
    assert "이십오쩜구구 달러" in out


def test_inline_backtick_quoted_english_preserve():
    text = (
        '개발팀은 `"The temperature is 25℃."`라는 예시를 남기고, '
        "실제 25℃와 pH 7.4는 처리해야 한다고 설명했습니다."
    )
    out = transform(text)
    assert out != text
    assert '`"The temperature is 25℃."`' in out
    assert "이십오도" in out
    assert "피에이치 칠쩜사" in out
    assert "라는 예시" in out


def test_inline_backtick_json_preserve_but_outside_transform():
    text = (
        '개발팀은 `{"text":"25℃"}`라고 입력했고, '
        "본문 온도 25℃와 pH 7.4는 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert '`{"text":"25℃"}`' in out
    assert "이십오도" in out
    assert "피에이치 칠쩜사" in out


def test_markdown_code_fence_preserve_but_outside_transform():
    text = (
        "개발팀은 아래 JSON 예시를 보존해야 한다고 설명했습니다.\n"
        "```json\n"
        '{"text":"25℃", "ph":"pH 7.4"}\n'
        "```\n"
        "하지만 본문 온도 25℃와 pH 7.4, $25.99는 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "```json\n" in out
    assert '{"text":"25℃", "ph":"pH 7.4"}' in out
    assert "```\n" in out
    assert "이십오도" in out
    assert "피에이치 칠쩜사" in out
    assert "이십오쩜구구 달러" in out


def test_markdown_shell_fence_preserve_but_outside_transform():
    text = (
        "운영팀은 아래 명령을 원문으로 남겼습니다.\n"
        "```bash\n"
        "curl -X POST http://localhost:8010/api/transform\n"
        "```\n"
        "그리고 실제 입력 25℃와 pH 7.4는 처리해야 합니다."
    )
    out = transform(text)
    assert out != text
    assert "curl -X POST http://localhost:8010/api/transform" in out
    assert "이십오도" in out
    assert "피에이치 칠쩜사" in out
