from pathlib import Path


def test_frontend_has_model_control_three_outputs_and_five_diffs() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert 'id="llm-model"' in web
    assert 'id="llm-enabled"' not in web
    for model in (
        "gemma4:e4b",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    ):
        assert model not in web

    for element_id in (
        "stage-1-output",
        "stage-1-diff",
        "stage-2-output",
        "stage-2-previous-diff",
        "stage-2-original-diff",
        "stage-3-output",
        "stage-3-previous-diff",
        "stage-3-original-diff",
    ):
        assert f'id="{element_id}"' in web


def test_frontend_runs_rule_prosody_and_speech_serially() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert 'fetch(`${getBackendBase()}/api/transform`' not in web
    assert "`${getBackendBase()}/api/transform`" in web
    assert "`${getBackendBase()}/api/llm/transform`" in web
    assert 'runLLMStage("prosody", normalizedText, selectedModel)' in web
    assert 'runLLMStage("speech", prosodyText, selectedModel)' in web
    assert "normalizedText = await runRuleStage(originalText)" in web
    assert "Promise.allSettled" not in web
    assert "if (stageName === \"prosody\"" not in web
    assert '[inputField]: inputText' in web
    assert "2단계 실패로 3단계를 실행하지 않았습니다." in web
    assert "1·2단계 결과는 유지됩니다." in web


def test_frontend_has_stage_colors_legend_and_provenance_rendering() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")
    diff_source = Path("web/pipeline_diff.js").read_text(encoding="utf-8")

    for stage in (1, 2, 3):
        assert f".diff-stage-{stage}" in web
        assert f"legend-stage-{stage}" in web
    assert "buildPipelineLedgers" in web
    assert "renderCumulativeDiff" in web
    assert "sourceIndex" in diff_source
    assert "stage," in diff_source
    assert "diff-space-symbol" in diff_source
    assert "diff-comma" in diff_source
    assert "MAX_LCS_CELLS" in diff_source
    assert "escapeHtml" in diff_source


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
