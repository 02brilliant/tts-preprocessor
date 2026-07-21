from __future__ import annotations

import importlib
import sys


def test_phase19d_importing_compare_cli_does_not_force_legacy_pipeline_import() -> None:
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}
    module = importlib.import_module("engine.span_engine.compare_cli")
    after = {name for name in sys.modules if name.startswith("engine.pipeline")}

    assert module is not None
    assert after == before


def test_phase19d_parse_compare_args_does_not_force_legacy_pipeline_import() -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    parse_compare_args = getattr(compare_cli, "parse_compare_args")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    parse_compare_args([])

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert after == before


def test_phase19d_run_compare_cli_no_legacy_is_graceful_when_legacy_missing(tmp_path) -> None:
    compare_cli = importlib.import_module("engine.span_engine.compare_cli")
    run_compare_cli = getattr(compare_cli, "run_compare_cli")
    before = {name for name in sys.modules if name.startswith("engine.pipeline")}

    exit_code = run_compare_cli(
        [
            "--use-default-corpus",
            "--jsonl",
            str(tmp_path / "report.jsonl"),
            "--no-legacy",
        ]
    )

    after = {name for name in sys.modules if name.startswith("engine.pipeline")}
    assert exit_code == 0
    assert after == before

