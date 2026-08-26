from pathlib import Path


def test_frontend_has_six_level_control_model_control_and_outputs() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert 'id="llm-model"' in web
    assert 'id="correction-level"' in web
    for level in range(6):
        assert f'data-correction-level="{level}"' in web
    assert "0단계<br>교정안함" in web
    assert "1단계<br>규칙간소화" in web
    assert "2단계<br>규칙기반교정" in web
    assert "3단계<br>LLM최소" in web
    assert "4단계<br>LLM자연스러운발화" in web
    assert "5단계<br>LLM발음강화(시험)" in web
    assert 'max="5"' in web
    assert 'aria-pressed="true"' in web
    assert 'class="pipeline-controls"' in web
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
    assert "규칙 처리 텍스트 복사" in web
    assert "LLM 처리 텍스트 복사" in web
    assert "setCopyableText(1, normalizedText)" in web
    assert "setCopyableText(2, displayedSpeechText)" in web
    assert "navigator.clipboard.writeText" in web
    assert 'id="stage-3-output"' not in web


def test_frontend_calls_one_transform_endpoint_for_every_level() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")

    assert "`${getBackendBase()}/api/transform`" in web
    assert "/api/llm/transform" not in web
    assert "runLLMStage" not in web
    assert "runRuleStage" not in web
    assert "prompt_level" not in web
    assert "level: selectedCorrectionLevel" in web
    assert "Promise.allSettled" not in web
    assert "JSON.stringify(requestBody)" in web
    assert "stage: stageName" not in web
    assert "prosody_text" not in web
    assert "규칙 처리 결과는 유지됩니다." in web
    assert "selectedCorrectionLevel === 0" in web
    assert "setCorrectionLevel(button.dataset.correctionLevel)" in web
    assert 'data.llm_called === false' in web
    assert "LLM 호출 생략 · 규칙 결과 사용" in web
    assert "data.rule_elapsed_ms" in web
    assert "data.llm_elapsed_ms" in web
    assert "규칙기반 처리시간" in web
    assert "LLM 처리시간" in web


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
    assert "typeof detail.speech_text" in web
    assert "LLM 원출력을 표시했습니다." in web
    assert "공백·줄바꿈·고정 문장부호 변경" in web
    assert "PipelineDiff.renderSpeechContractViolation" in web
    assert "invalidStage2Ledgers" in web
    assert "규칙 처리 결과는 유지됩니다." in web


def test_frontend_displays_level5_rejected_llm_output_with_failure_marking() -> None:
    web = Path("web/index.html").read_text(encoding="utf-8")
    diff_source = Path("web/pipeline_diff.js").read_text(encoding="utf-8")

    assert "rejected_speech_text" in web
    assert "LLM 검증 실패 · 규칙 결과를 최종 출력으로 사용" in web
    assert "거절된 변경을 주황색으로 표시했습니다." in web
    assert 'type: "contract_violation"' in diff_source
    assert 'type: "contract_violation_deleted"' in diff_source


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
