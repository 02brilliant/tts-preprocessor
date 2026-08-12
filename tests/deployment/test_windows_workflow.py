from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW = Path(".github/workflows/build-desktop-executables.yml")
BUILD_REQUIREMENTS = Path("requirements/build.txt")


def _load_workflow() -> dict[str, object]:
    # BaseLoader preserves the YAML key "on" as text instead of applying the
    # YAML 1.1 boolean coercion used by SafeLoader.
    loaded = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(loaded, dict)
    return loaded


def test_windows_workflow_is_manual_and_windows_only() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    parsed = _load_workflow()
    triggers = parsed["on"]
    jobs = parsed["jobs"]

    assert "name: Build Windows executable" in workflow
    assert isinstance(triggers, dict)
    assert set(triggers) == {"workflow_dispatch"}
    assert isinstance(jobs, dict)
    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    assert isinstance(job, dict)
    assert job["runs-on"] == "windows-latest"
    assert "strategy" not in job
    assert "matrix" not in job
    steps = job["steps"]
    assert isinstance(steps, list)
    setup_python = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("uses") == "actions/setup-python@v5"
    ]
    assert len(setup_python) == 1
    assert setup_python[0]["with"]["python-version"] == "3.13.14"
    assert "sys.version_info[:2] == (3, 13)" in workflow
    assert "Py_GIL_DISABLED" in workflow
    assert "macos-latest" not in workflow
    assert "ubuntu-latest" not in workflow


def test_windows_workflow_builds_smokes_and_uploads_one_flat_zip() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    parsed = _load_workflow()
    jobs = parsed["jobs"]
    job = next(iter(jobs.values()))
    steps = job["steps"]
    upload_steps = [
        step
        for step in steps
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/upload-artifact@")
    ]

    build_requirements = BUILD_REQUIREMENTS.read_text(encoding="utf-8")
    assert "-r requirements/build.txt" in workflow
    assert "pyinstaller==6.21.0" in build_requirements
    assert "pyinstaller-hooks-contrib==2026.6" in build_requirements
    assert "pyinstaller_runtime_hooks" not in workflow
    assert "tts_preprocessor.spec" in workflow
    assert "tts_llm_stage.spec" in workflow
    assert "build_binary_entrypoint" in workflow
    assert "build_llm_stage_entrypoint" in workflow
    assert "dist\\tts-preprocessor.exe" in workflow
    assert "dist\\tts-llm-stage.exe" in workflow
    assert "Smoke test executable" in workflow
    assert "Extracted Windows executable smoke test failed" in workflow
    assert '$expected = @("README.txt", "tts-llm-stage.exe", "tts-preprocessor.exe")' in workflow
    assert "artifact\\tts-preprocessor-windows.zip" in workflow
    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["path"] == (
        "artifact/tts-preprocessor-windows.zip"
    )
    assert "if-no-files-found: error" in workflow
