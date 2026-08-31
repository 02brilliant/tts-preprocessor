from __future__ import annotations

from pathlib import Path


PACKAGED_PATHSPEC = (
    "engine",
    "bin",
    "LLM",
    "tts_preprocessor.spec",
    "tts_preprocessor_simplified.spec",
    "tts_preprocessor_llm_minimal.spec",
    "tts_preprocessor_llm_natural.spec",
    "scripts/probes",
)


def test_deploy_with_gates_script_exists_and_wraps_deploy_server() -> None:
    script = Path("scripts/deploy_with_gates.sh").read_text(encoding="utf-8")

    assert script.startswith("#!/usr/bin/env bash")
    assert 'bash "$DEPLOY_SERVER_SCRIPT"' in script or "bash \"$DEPLOY_SERVER_SCRIPT\"" in script
    assert "scripts/deploy_server.sh" in script
    assert "commit_packaged_worktree_if_needed" in script
    assert "DEPLOY_SKIP_COMMIT" in script
    assert "DEPLOY_COMMIT_MESSAGE" in script
    assert "git -C" in script and "commit -m" in script
    assert "DEPLOY_EXTERNAL_API_PROBE" in script
    assert "DEPLOY_SERVER_HOST" in script
    assert "run_semantic_probes.py" in script
    assert "--runtime api" in script
    assert "check_server.sh" not in script
    commit_index = script.index("commit_packaged_worktree_if_needed")
    deploy_index = script.index('bash "$DEPLOY_SERVER_SCRIPT"')
    assert commit_index < deploy_index


def test_deploy_with_gates_commits_the_same_packaged_pathspec_as_deploy_server() -> None:
    gates = Path("scripts/deploy_with_gates.sh").read_text(encoding="utf-8")
    deploy = Path("scripts/deploy_server.sh").read_text(encoding="utf-8")

    for path in PACKAGED_PATHSPEC:
        assert path in gates
        assert path in deploy
