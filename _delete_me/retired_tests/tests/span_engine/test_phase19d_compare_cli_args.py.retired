from __future__ import annotations

import importlib


def test_phase19d_parse_compare_args_default_corpus() -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    parse_compare_args = getattr(compare_cli, "parse_compare_args")

    args = parse_compare_args([])

    assert getattr(args, "input", None) is None
    assert getattr(args, "jsonl", None) is None
    assert getattr(args, "markdown", None) is None
    assert getattr(args, "include_debug", False) is False
    assert getattr(args, "no_legacy", False) is False
    assert getattr(args, "use_default_corpus", False) is True


def test_phase19d_parse_compare_args_explicit_paths() -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    parse_compare_args = getattr(compare_cli, "parse_compare_args")

    args = parse_compare_args(
        [
            "--input",
            "cases.txt",
            "--jsonl",
            "out.jsonl",
            "--markdown",
            "out.md",
            "--include-debug",
            "--no-legacy",
        ]
    )

    assert getattr(args, "input", None) == "cases.txt"
    assert getattr(args, "jsonl", None) == "out.jsonl"
    assert getattr(args, "markdown", None) == "out.md"
    assert getattr(args, "include_debug", False) is True
    assert getattr(args, "no_legacy", False) is True

