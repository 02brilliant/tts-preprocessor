from pathlib import Path


def test_frontend_has_llm_toggle_model_control_and_two_stage_outputs() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert 'id="llm-model"' in web
    assert 'id="llm-toggle"' in web
    assert 'aria-pressed="true"' in web
    assert "LLM 추가교정 설정" in web
    assert 'class="llm-controls"' in web
    for model in (
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    ):
        assert model in web
    assert "HIDDEN_LLM_MODELS" in web
    assert "visibleModels = data.models.filter" in web

    for element_id in (
        "stage-1-output",
        "stage-1-diff",
        "stage-1-copy",
        "stage-2-output",
        "stage-2-previous-diff",
        "stage-2-original-diff",
        "stage-2-copy",
    ):
        assert f'id="{element_id}"' in web
    assert "1단계 발음교정 텍스트 복사" in web
    assert "2단계 발음교정 텍스트 복사" in web
    assert "setCopyableText(1, data.normalized_text)" in web
    assert "setCopyableText(2, data.speech_text)" in web
    assert "navigator.clipboard.writeText" in web
    assert 'id="stage-3-output"' not in web


def test_frontend_runs_rule_and_integrated_llm_serially() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert 'fetch(`${getBackendBase()}/api/transform`' not in web
    assert "`${getBackendBase()}/api/transform`" in web
    assert "`${getBackendBase()}/api/llm/transform`" in web
    assert "runLLMStage(normalizedText, selectedModel)" in web
    assert "normalizedText = await runRuleStage(originalText)" in web
    assert "Promise.allSettled" not in web
    assert "normalized_text: normalizedText" in web
    assert "stage: stageName" not in web
    assert "prosody_text" not in web
    assert "1단계 실패로 2단계를 실행하지 않았습니다." in web
    assert "1단계 결과는 유지됩니다." in web
    assert "LLM 추가교정은 OFF 상태입니다." in web
    assert "setLLMEnabled(!llmEnabled)" in web


def test_frontend_has_stage_colors_legend_and_provenance_rendering() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")
    diff_source = Path("web/pipeline_diff.js").read_text(encoding="utf-8")

    for stage in (1, 2):
        assert f".diff-stage-{stage}" in web
        assert f"legend-stage-{stage}" in web
    assert ".diff-stage-3" not in web
    assert "legend-stage-3" not in web
    assert "buildPipelineLedgers" in web
    assert "renderCumulativeDiff" in web
    assert "sourceIndex" in diff_source
    assert "stage," in diff_source
    assert "diff-space-symbol" in diff_source
    assert "diff-comma" in diff_source
    assert "MAX_LCS_CELLS" in diff_source
    assert "escapeHtml" in diff_source
    assert ".diff-contract-violation" in web
    assert "legend-violation" in web
    assert "renderSpeechContractViolation" in web
    assert "renderStage1Input" in web
    assert "speechContractParts" in diff_source
    assert "stage1InputParts" in diff_source
    assert 'type: "stage1_modified"' in diff_source
    assert '"unprocessed_alphanumeric"' in diff_source
    assert ".diff-stage-1-input-modified" in web
    assert 'type: "contract_violation"' in diff_source
    assert '"contract_violation_deleted"' in diff_source


def test_frontend_preserves_contract_violating_llm_output() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert "error.contractDetail = detail" in web
    assert "error.stageOutput = contractOutput" in web
    assert "LLM 원출력을 표시했습니다." in web
    assert "공백·줄바꿈·고정 문장부호 변경" in web
    assert "PipelineDiff.renderSpeechContractViolation" in web
    assert "invalidStage2Ledgers" in web
    assert "1단계 결과는 유지됩니다." in web


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
