from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.span_engine.compare import (
    CompareCorpusReport,
    export_compare_jsonl,
    export_compare_markdown,
    run_default_compare_report,
    write_compare_jsonl,
    write_compare_markdown,
)


def build_rollout_gate_result(
    report: CompareCorpusReport | dict[str, Any],
    *,
    strict: bool = False,
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_obj = _coerce_report(report)
    summary = dict(report_obj.summary)
    span_error_count = _count_span_errors(report_obj)
    suspicious_count = max(
        int(summary.get("suspicious_count", summary.get("suspicious_diff", 0)) or 0),
        _count_categories(report_obj, "suspicious_diff"),
    )
    legacy_error_fixed = max(
        int(summary.get("legacy_error_fixed", 0) or 0),
        _count_categories(report_obj, "legacy_error_fixed"),
    )
    unsupported = max(
        int(summary.get("unsupported", 0) or 0),
        _count_categories(report_obj, "unsupported"),
    )

    blocking_reasons: list[str] = []
    review_reasons: list[str] = []

    if span_error_count > 0:
        blocking_reasons.append(f"span_error:{span_error_count}")
    if unsupported > 0 and strict:
        blocking_reasons.append(f"unsupported:{unsupported}")
    if suspicious_count > 0:
        review_reasons.append(f"suspicious_diff:{suspicious_count}")
    if legacy_error_fixed > 0:
        review_reasons.append(f"legacy_error_fixed:{legacy_error_fixed}")
    if unsupported > 0 and not strict:
        review_reasons.append(f"unsupported:{unsupported}")

    if span_error_count > 0:
        status = "fail"
    elif unsupported > 0 and strict:
        status = "fail"
    elif suspicious_count > 0 or legacy_error_fixed > 0 or (unsupported > 0 and not strict):
        status = "review_required"
    else:
        status = "pass"

    gate_result = {
        "ok": status == "pass",
        "status": status,
        "summary": summary,
        "blocking_reasons": blocking_reasons,
        "review_reasons": review_reasons,
        "report": report_obj.to_dict(),
        "artifacts": None if artifacts is None else dict(artifacts),
    }
    return gate_result


def run_default_rollout_gate(
    *,
    legacy_transform: Any | None = None,
    include_debug: bool = False,
    strict: bool = False,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    report = run_default_compare_report(
        legacy_transform=legacy_transform,
        include_debug=include_debug,
    )
    gate_result = build_rollout_gate_result(report, strict=strict)

    if artifact_dir is not None:
        artifacts = write_rollout_gate_artifacts(gate_result, report, artifact_dir)
        gate_result["artifacts"] = artifacts

    return gate_result


def write_rollout_gate_artifacts(
    gate_result: dict[str, Any],
    report: CompareCorpusReport | dict[str, Any],
    artifact_dir: str | Path,
    *,
    basename: str = "rollout_gate",
) -> dict[str, Any]:
    _ = gate_result
    report_obj = _coerce_report(report)
    target_dir = Path(artifact_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = target_dir / f"{basename}.jsonl"
    markdown_path = target_dir / f"{basename}.md"
    write_compare_jsonl(report_obj, jsonl_path)
    write_compare_markdown(report_obj, markdown_path)
    return {
        "jsonl": jsonl_path,
        "markdown": markdown_path,
    }


def _coerce_report(report: CompareCorpusReport | dict[str, Any]) -> CompareCorpusReport:
    if isinstance(report, CompareCorpusReport):
        return report
    return CompareCorpusReport.from_dict(report)


def _count_span_errors(report: CompareCorpusReport) -> int:
    return sum(1 for result in report.results if bool(result.span_error))


def _count_categories(report: CompareCorpusReport, category: str) -> int:
    return sum(1 for result in report.results if result.category == category)


__all__ = [
    "build_rollout_gate_result",
    "run_default_rollout_gate",
    "write_rollout_gate_artifacts",
]
