from __future__ import annotations

import importlib


def test_phase20h_rollout_gate_helper_artifacts_are_written(tmp_path) -> None:
    gate_module = importlib.import_module("engine.span_engine.rollout_gate")
    run_default_rollout_gate = getattr(gate_module, "run_default_rollout_gate")

    result = run_default_rollout_gate(legacy_transform=lambda text: text, artifact_dir=tmp_path)

    assert result["artifacts"] is not None
    jsonl_path = result["artifacts"]["jsonl"]
    markdown_path = result["artifacts"]["markdown"]
    assert jsonl_path.exists()
    assert markdown_path.exists()
    assert jsonl_path.read_text(encoding="utf-8")
    assert "# Compare Report" in markdown_path.read_text(encoding="utf-8")
