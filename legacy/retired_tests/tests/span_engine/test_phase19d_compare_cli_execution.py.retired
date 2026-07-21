from __future__ import annotations

import importlib


def test_phase19d_run_compare_cli_default_corpus_without_legacy(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    run_compare_cli = getattr(compare_cli, "run_compare_cli")

    jsonl_path = tmp_path / "out" / "report.jsonl"
    md_path = tmp_path / "out" / "report.md"

    exit_code = run_compare_cli(
        [
            "--use-default-corpus",
            "--jsonl",
            str(jsonl_path),
            "--markdown",
            str(md_path),
            "--no-legacy",
        ]
    )

    assert exit_code == 0
    assert jsonl_path.exists()
    assert md_path.exists()


def test_phase19d_run_compare_cli_include_debug_does_not_crash(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    run_compare_cli = getattr(compare_cli, "run_compare_cli")

    jsonl_path = tmp_path / "report.jsonl"

    exit_code = run_compare_cli(
        [
            "--use-default-corpus",
            "--jsonl",
            str(jsonl_path),
            "--include-debug",
            "--no-legacy",
        ]
    )

    assert exit_code == 0
    assert jsonl_path.exists()

