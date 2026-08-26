from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import statistics
import time
import urllib.error
import urllib.request

from LLM.invocation_gate import decide_llm_invocation
from LLM.paragraph_parallel import split_paragraph_units
from LLM.provenance import build_normalization_snapshot
from LLM.response_validation import LLMStageContractError, validate_speech_text
from LLM.stage_engine import transform as transform_llm
from engine.main import transform_output


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    text: str
    expected_stage4: tuple[str, ...] = ()
    expected_stage5: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


CASES = (
    EvaluationCase("numeric_unit", "발전소는 55MW를 공급했습니다."),
    EvaluationCase(
        "protected",
        "자료는 https://example.com/report_v2.json과 SKU-H100-25에 있습니다.",
    ),
    EvaluationCase(
        "general_g2p_negative",
        "국물은 같이 읽고 있습니다.",
        forbidden=("궁물", "궁무른", "가치", "읻씀니다"),
    ),
    EvaluationCase("stage4_n", "색연필입니다.", expected_stage4=("색년필",), expected_stage5=("색년필",)),
    EvaluationCase("stage4_tense", "문고리를 잡았습니다.", expected_stage4=("문꼬리",), expected_stage5=("문꼬리",)),
    EvaluationCase("stage4_contraction", "기자입니다.", expected_stage4=("기잡니다",), expected_stage5=("기잡니다",)),
    EvaluationCase("stage5_nl", "생산량은 증가량과 다릅니다.", expected_stage5=("생산냥",), forbidden=("증가냥",)),
    EvaluationCase("stage5_rate", "백분율을 공개했습니다.", expected_stage5=("백뿐뉼",)),
    EvaluationCase("daega_reward", "노동의 대가를 지급했습니다.", expected_stage5=("대까",)),
    EvaluationCase("daega_master", "예술계의 대가를 만났습니다.", forbidden=("대까",)),
    EvaluationCase("daega_uncertain", "그는 대가에 관해 말했습니다.", forbidden=("대까",)),
    EvaluationCase("singo_contrast", "신발을 신고 경찰에 신고했습니다.", forbidden=("신꼬", "신고를")),
    EvaluationCase(
        "multi_paragraph",
        "생산량은 늘었습니다. 증가량은 별도 집계했습니다.\n\n"
        "예술계의 대가가 의견란을 검토했습니다.",
        expected_stage5=("생산냥", "의견난"),
        forbidden=("증가냥", "대까"),
    ),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-api", required=True)
    parser.add_argument("--model", default="gemma4-31B-it (vLLM)")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument(
        "--configuration",
        choices=(
            "A_baseline_level3",
            "B_improved_level3",
            "C_baseline_level4",
            "D_improved_level4",
            "E_new_level5",
        ),
    )
    return parser


def _baseline_call(
    *,
    api: str,
    case: EvaluationCase,
    stage: int,
    model: str,
) -> dict:
    body = json.dumps(
        {"text": case.text, "level": stage, "model": model},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        api.rstrip("/") + "/api/transform",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read())
        status = 200
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read())
        status = exc.code
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "status": status,
        "speech_text": payload.get("speech_text"),
        "normalized_text": payload.get("normalized_text"),
        "elapsed_ms": elapsed_ms,
        "provider_elapsed_ms": payload.get("elapsed_ms"),
        "llm_called": payload.get("llm_called"),
        "upstream_calls": 1 if payload.get("llm_called") else 0,
        "prompt_tokens": None,
        "completion_tokens": None,
        "error": payload.get("detail"),
    }


def _current_call(case: EvaluationCase, *, stage: int, model: str) -> dict:
    prompt_level = stage - 2
    rule_output = transform_output(case.text)
    normalized_text = rule_output.normalized_text
    snapshot = build_normalization_snapshot(rule_output)
    decision = decide_llm_invocation(normalized_text, stage_level=stage)
    if not decision.call_llm:
        return {
            "status": 200,
            "speech_text": normalized_text,
            "normalized_text": normalized_text,
            "elapsed_ms": 0.0,
            "provider_elapsed_ms": 0.0,
            "llm_called": False,
            "upstream_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "fallback": False,
            "error": None,
        }
    chunks, _ = split_paragraph_units(normalized_text)
    upstream_calls = sum(bool(chunk.strip()) for chunk in chunks)
    started = time.perf_counter()
    try:
        result = transform_llm(
            normalized_text,
            model=model,
            prompt_level=prompt_level,
            snapshot=snapshot,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "status": 200,
            "speech_text": result.speech_text,
            "normalized_text": normalized_text,
            "elapsed_ms": elapsed_ms,
            "provider_elapsed_ms": result.elapsed_ms,
            "llm_called": True,
            "upstream_calls": upstream_calls,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "fallback": result.validation_fallback,
            "error": [asdict(issue) for issue in result.validation_issues] or None,
        }
    except LLMStageContractError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "status": 502,
            "speech_text": exc.output_text,
            "normalized_text": normalized_text,
            "elapsed_ms": elapsed_ms,
            "provider_elapsed_ms": None,
            "llm_called": True,
            "upstream_calls": upstream_calls,
            "prompt_tokens": None,
            "completion_tokens": None,
            "fallback": False,
            "error": {"code": exc.code, "severity": exc.severity},
        }


def _score(case: EvaluationCase, result: dict, stage: int) -> dict:
    speech_text = result.get("speech_text")
    normalized_text = result.get("normalized_text")
    if not isinstance(speech_text, str) or not isinstance(normalized_text, str):
        return {"validator_ok": False, "pronunciation_fn": 0, "pronunciation_fp": 0}
    validation = validate_speech_text(
        normalized_text,
        speech_text,
        stage=stage,
    )
    expected = case.expected_stage5 if stage == 5 else case.expected_stage4 if stage == 4 else ()
    return {
        "validator_ok": validation.ok,
        "validation_codes": [issue.code for issue in validation.issues],
        "pronunciation_fn": sum(item not in speech_text for item in expected),
        "pronunciation_fp": sum(item in speech_text for item in case.forbidden),
    }


def _summary(rows: list[dict]) -> dict:
    latencies = sorted(row["elapsed_ms"] for row in rows)
    provider_latencies = sorted(
        row["provider_elapsed_ms"]
        for row in rows
        if row["llm_called"]
        and isinstance(row["provider_elapsed_ms"], (int, float))
    )
    prompt_usage = [row["prompt_tokens"] for row in rows if row["prompt_tokens"] is not None]
    completion_usage = [row["completion_tokens"] for row in rows if row["completion_tokens"] is not None]
    percentile = lambda fraction: latencies[min(len(latencies) - 1, int((len(latencies) - 1) * fraction))]
    provider_percentile = lambda fraction: provider_latencies[
        min(len(provider_latencies) - 1, int((len(provider_latencies) - 1) * fraction))
    ]
    return {
        "samples": len(rows),
        "status_failures": sum(row["status"] != 200 for row in rows),
        "validator_failures": sum(not row["score"]["validator_ok"] for row in rows),
        "pronunciation_fn": sum(row["score"]["pronunciation_fn"] for row in rows),
        "pronunciation_fp": sum(row["score"]["pronunciation_fp"] for row in rows),
        "fallbacks": sum(bool(row.get("fallback")) for row in rows),
        "llm_called_samples": sum(bool(row["llm_called"]) for row in rows),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": percentile(0.95),
        "latency_p99_observed_ms": percentile(0.99),
        "provider_latency_p50_ms": (
            statistics.median(provider_latencies) if provider_latencies else None
        ),
        "provider_latency_p95_ms": (
            provider_percentile(0.95) if provider_latencies else None
        ),
        "upstream_calls": sum(row["upstream_calls"] for row in rows),
        "prompt_tokens_observed": sum(prompt_usage) if len(prompt_usage) == len(rows) else None,
        "completion_tokens_observed": sum(completion_usage) if len(completion_usage) == len(rows) else None,
        "validation_code_counts": {
            code: sum(code in row["score"].get("validation_codes", ()) for row in rows)
            for code in sorted(
                {
                    code
                    for row in rows
                    for code in row["score"].get("validation_codes", ())
                }
            )
        },
    }


def main() -> int:
    args = _parser().parse_args()
    configurations = (
        ("A_baseline_level3", 3, "baseline"),
        ("B_improved_level3", 3, "current"),
        ("C_baseline_level4", 4, "baseline"),
        ("D_improved_level4", 4, "current"),
        ("E_new_level5", 5, "current"),
    )
    output: dict[str, dict] = {}
    for name, stage, mode in configurations:
        if args.configuration is not None and name != args.configuration:
            continue
        rows = []
        for case in CASES:
            result = (
                _baseline_call(
                    api=args.baseline_api,
                    case=case,
                    stage=stage,
                    model=args.model,
                )
                if mode == "baseline"
                else _current_call(case, stage=stage, model=args.model)
            )
            result["case_id"] = case.case_id
            result["score"] = _score(case, result, stage)
            rows.append(result)
        output[name] = {"summary": _summary(rows), "rows": rows}
    rendered = (
        {name: result["summary"] for name, result in output.items()}
        if args.summary_only
        else output
    )
    print(json.dumps(rendered, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
