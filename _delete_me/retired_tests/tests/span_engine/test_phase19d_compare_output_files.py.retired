from __future__ import annotations

import importlib


def test_phase19d_jsonl_and_markdown_output_files_are_written(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    run_compare_cli = getattr(compare_cli, "run_compare_cli")

    jsonl_path = tmp_path / "nested" / "compare.jsonl"
    md_path = tmp_path / "nested" / "compare.md"

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
    assert jsonl_path.read_text(encoding="utf-8").strip()
    assert "# Compare Report" in md_path.read_text(encoding="utf-8")


def test_phase19d_output_files_can_be_overwritten(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    run_compare_cli = getattr(compare_cli, "run_compare_cli")

    jsonl_path = tmp_path / "compare.jsonl"
    md_path = tmp_path / "compare.md"
    jsonl_path.write_text("old", encoding="utf-8")
    md_path.write_text("old", encoding="utf-8")

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
    assert jsonl_path.read_text(encoding="utf-8") != "old"
    assert md_path.read_text(encoding="utf-8") != "old"

