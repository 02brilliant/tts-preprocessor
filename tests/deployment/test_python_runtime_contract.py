from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_python_patch_and_supported_series_are_explicit() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.13.14"

    for relative in (
        "scripts/build_macos_package.sh",
        "scripts/build_binary.sh",
        "scripts/build_remote_package.sh",
        "scripts/deploy_server.sh",
        "scripts/release.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "3.13" in text
        assert "Py_GIL_DISABLED" in text


def test_direct_dependencies_are_split_by_runtime_build_and_development() -> None:
    runtime = (ROOT / "requirements/runtime.txt").read_text(encoding="utf-8")
    build = (ROOT / "requirements/build.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements/dev.txt").read_text(encoding="utf-8")

    assert "fastapi==0.139.2" in runtime
    assert "pydantic==2.13.4" in runtime
    assert "uvicorn==0.51.0" in runtime
    assert "pyinstaller==6.21.0" in build
    assert "pyinstaller-hooks-contrib==2026.6" in build
    assert "-r runtime.txt" in dev
    assert "-r build.txt" in dev
    assert "pytest==9.1.1" in dev
    assert "PyYAML==6.0.3" in dev
    assert "httpx2==2.7.0" in dev


def test_deploy_preflight_checks_api_and_build_python_before_sync() -> None:
    deploy = (ROOT / "scripts/deploy_server.sh").read_text(encoding="utf-8")
    remote_preflight = deploy.index(
        'echo "[deploy] Checking the existing remote Linux build environment..."'
    )
    source_sync = deploy.index(
        'echo "[deploy] Preparing isolated remote buildsrc..."'
    )

    assert 'runtime_python="$remote_base_dir/.venv/bin/python"' in deploy
    assert 'for python_bin in "$runtime_python" "$buildenv_dir/bin/python"' in deploy
    assert 'if [[ "$python_runtime" != "3.13:0" ]]' in deploy
    assert remote_preflight < source_sync
