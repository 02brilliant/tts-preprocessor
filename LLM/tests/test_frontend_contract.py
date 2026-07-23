from pathlib import Path


def test_frontend_has_independent_llm_controls_results_and_timing() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert 'id="llm-enabled"' in web
    assert 'id="llm-enabled" type="checkbox" checked' in web
    assert 'id="llm-model"' in web
    assert "gemma4:e4b" not in web
    assert 'id="llm-output"' in web
    assert 'id="llm-diff"' in web
    assert 'id="rule-timing"' in web
    assert 'id="llm-timing"' in web
    assert 'id="llm-error"' in web


def test_frontend_parallelizes_and_isolates_rule_and_llm_requests() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert "Promise.allSettled" in web
    assert "runRuleTransform(text)" in web
    assert "runLLMTransform(text)" in web
    assert 'fetch(`${getBackendBase()}/api/transform`' in web
    assert 'fetch(`${getBackendBase()}/api/llm/models`' in web
    assert 'fetch(`${getBackendBase()}/api/llm/transform`' in web
    assert "getLLMBase" not in web
    assert "8020" not in web
    assert "if (llmEnabledEl.checked)" in web
    assert "renderDiff(text, normalizedText, diffEl)" in web
    assert "renderDiff(text, llmText, llmDiffEl)" in web


def test_existing_download_contract_remains() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    for archive_name in (
        "tts-preprocessor-linux.zip",
        "tts-preprocessor-macos.zip",
        "tts-preprocessor-windows.zip",
    ):
        assert archive_name in web
    assert "DOWNLOAD_TARGETS.map(async (target)" in web
    assert "Promise.all(" in web
