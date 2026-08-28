from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def parse_args(*, stage_level: int) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Run the integrated stage-{stage_level} TTS preprocessor."
    )
    parser.add_argument("--input", help="Original input text file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--text", help="Original text to process directly")
    parser.add_argument("--model", help="Configured LLM model ID")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit normalized_text and speech_text as JSON.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print configured model IDs as JSON and exit.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate bundled rule, prompt, and model assets without calling an LLM.",
    )
    return parser.parse_args()


def _read_input_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    return sys.stdin.read()


def _write_output(output_text: str, *, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(output_text, encoding="utf-8")
        return
    print(output_text)


def _print_json(payload: dict, *, stream=None) -> None:
    print(
        json.dumps(payload, ensure_ascii=False),
        file=sys.stdout if stream is None else stream,
    )


def run(*, stage_level: int, prompt_level: int) -> int:
    if (stage_level, prompt_level) not in {(3, 1), (4, 2)}:
        raise ValueError("integrated stage mapping must be 3/1 or 4/2")

    from LLM.cli_protocol import classify_llm_stage_error
    from LLM.config import load_model_config
    from LLM.invocation_gate import decide_llm_invocation
    from LLM.pronunciation_overlay import apply_pronunciation_overlay
    from LLM.stage_engine import transform as transform_llm
    from LLM.stage_engine import UnsupportedLLMModelError
    from LLM.stage_engine import validate_runtime_assets
    from engine.main import transform_output
    from LLM.provenance import build_normalization_snapshot

    args = parse_args(stage_level=stage_level)
    normalized_text: str | None = None
    rule_elapsed_ms = 0.0
    llm_elapsed_ms = 0.0
    upstream_elapsed_ms = 0.0
    rejected_speech_text: str | None = None
    validation_issue = None
    try:
        if args.list_models:
            model_config = load_model_config()
            _print_json(
                {
                    "models": list(model_config.models),
                    "default_model": model_config.default_model,
                }
            )
            return 0
        if args.check:
            validate_runtime_assets(prompt_levels=(prompt_level,))
            rule_probe = transform_output("ABC와 3kg").normalized_text
            if rule_probe != "에이비씨와 삼 킬로그램":
                raise RuntimeError("bundled rule engine self-check failed")
            if args.json:
                _print_json({"ok": True, "ready": True, "level": stage_level})
            else:
                print(f"Integrated stage {stage_level} runtime ready.")
            return 0

        original_text = _read_input_text(args)
        rule_started_at = time.perf_counter()
        rule_output = transform_output(original_text)
        normalized_text = rule_output.normalized_text
        snapshot = build_normalization_snapshot(rule_output)
        overlay = apply_pronunciation_overlay(
            normalized_text,
            stage=stage_level,
            snapshot=snapshot,
        )
        llm_input_text = overlay.text
        llm_snapshot = overlay.snapshot
        rule_elapsed_ms = (time.perf_counter() - rule_started_at) * 1000
        decision = decide_llm_invocation(
            llm_input_text,
            stage_level=stage_level,
        )
        if decision.call_llm:
            llm_started_at = time.perf_counter()
            result = transform_llm(
                llm_input_text,
                model=args.model,
                prompt_level=prompt_level,
                snapshot=llm_snapshot,
            )
            llm_elapsed_ms = (time.perf_counter() - llm_started_at) * 1000
            speech_text = result.speech_text
            selected_model = result.model
            upstream_elapsed_ms = result.elapsed_ms
            if result.validation_fallback:
                rejected_speech_text = result.rejected_speech_text
                validation_issue = result.validation_issues[0]
        else:
            model_config = load_model_config()
            selected_model = args.model or model_config.default_model
            if model_config.get(selected_model) is None:
                raise UnsupportedLLMModelError("Unsupported LLM model.")
            speech_text = llm_input_text
    except Exception as exc:
        status, detail = classify_llm_stage_error(exc)
        if args.json or args.list_models:
            error_payload = {"ok": False, "status": status, "detail": detail}
            if normalized_text is not None:
                error_payload["normalized_text"] = normalized_text
            _print_json(
                error_payload,
                stream=sys.stderr,
            )
        else:
            print(f"Integrated stage {stage_level} failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        response_payload = {
                "ok": True,
                "level": stage_level,
                "normalized_text": normalized_text,
                "speech_text": speech_text,
                "model": selected_model,
                # elapsed_ms is retained for clients that already use the
                # provider request duration. The two explicit fields are the
                # integrated runtime timings shown by the web UI.
                "elapsed_ms": round(upstream_elapsed_ms, 3),
                "rule_elapsed_ms": round(rule_elapsed_ms, 3),
                "llm_elapsed_ms": round(llm_elapsed_ms, 3),
                "llm_called": decision.call_llm,
                "llm_skip_reason": None if decision.call_llm else decision.reason,
        }
        if rejected_speech_text is not None and validation_issue is not None:
            response_payload["rejected_speech_text"] = rejected_speech_text
            response_payload["validation_failure"] = {
                "code": validation_issue.code,
                "severity": validation_issue.severity,
                "message": validation_issue.message,
            }
            if validation_issue.output_start is not None and validation_issue.output_end is not None:
                response_payload["validation_failure"]["output_start"] = validation_issue.output_start
                response_payload["validation_failure"]["output_end"] = validation_issue.output_end
        _print_json(response_payload)
        return 0

    _write_output(speech_text, output_path=args.output)
    return 0


__all__ = ["parse_args", "run"]
