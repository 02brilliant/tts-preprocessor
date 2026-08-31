"""Document contracts for level_policy.md and deployment_policy.md."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
LEVEL_POLICY = DOCS / "TTS_Preprocessor_level_policy.md"
DEPLOYMENT_POLICY = DOCS / "TTS_Preprocessor_deployment_policy.md"


def test_level_and_deployment_policy_files_exist() -> None:
    assert LEVEL_POLICY.is_file()
    assert DEPLOYMENT_POLICY.is_file()


def test_level_policy_stage_contract_phrases() -> None:
    text = LEVEL_POLICY.read_text(encoding="utf-8")

    for phrase in [
        "0~4단계 책임과 단계 간 계약의 단일 기준점",
        "| 0 | 없음 | 없음 | 원문 passthrough |",
        "| 1 | `simplified` | 없음 |",
        "| 2 | `default` | 없음 |",
        "| 3 | `default` | level 1, `LLM_prompt.txt` |",
        "| 4 | `default` | level 2, `LLM_prompt_lv2.txt` |",
        "다른 LLM 단계의 출력 문자열을 다음 단계 입력으로 사용하지 않는다",
        "ASCII 하이픈 U+002D(`-`)",
        "1번째→첫-번째",
        "5kg/5 kg→오-킬로그램",
        "stage4_base_text",
        "rejected_speech_text",
        "validation_failure",
        "Critical/High 검증 실패는 retry 없이",
        "## 품질 승인 기준",
        "2단계 기존 출력 byte-exact 100% 동일",
        "prompt placeholder 정확히 한 개",
        "이번 구현에서는 어느 항목도 1·2단계 출력에 적용하지 않았다",
    ]:
        assert phrase in text, phrase


def test_deployment_policy_must_phrases() -> None:
    text = DEPLOYMENT_POLICY.read_text(encoding="utf-8")

    for phrase in [
        "TTS_PREPROCESSOR_BINARY",
        "The API MUST NOT import `engine.*` to serve production transformations",
        "Linux production binaries MUST NOT be built on macOS or GitHub Actions",
        "standard-GIL Python 3.13",
        "standard-GIL CPython 3.13",
        "`-dirty` marker",
        "packaged-path status",
        "source debug fallback for packaged binaries without `--include-debug`",
        "`include_debug=true` payload may expose `trace.contextual_decision_logs`",
        "Ordinary binary output and ordinary `/api/transform` responses MUST NOT expose",
        "Deployment MUST NOT attach `contextual_decision_logs`",
        "`1㎘당`, `1만㎡`, `수 km`, `지상 3층`, `3.5만kg`, and `45~50만kg`",
        "gemma4-31B-it (vLLM)",
        "scripts/probes/",
    ]:
        assert phrase in text, phrase
