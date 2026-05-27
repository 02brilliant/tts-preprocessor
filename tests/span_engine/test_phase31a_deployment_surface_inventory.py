from __future__ import annotations

import ast
import os
import zipfile
from pathlib import Path


def test_phase31a_required_scripts_and_artifacts_exist() -> None:
    for path in (
        Path("scripts/build_binary.sh"),
        Path("scripts/build_package.py"),
        Path("scripts/start_server.sh"),
        Path("scripts/deploy_server.sh"),
        Path("scripts/release.py"),
        Path("scripts/build_remote_package.sh"),
        Path("api/server.py"),
        Path("api/binary_runtime.py"),
        Path("bin/build_binary_entrypoint.py"),
    ):
        assert path.exists(), path

    for path in (
        Path("dist/tts_preprocessor"),
        Path("packages/tts-preprocessor/bin/tts_preprocessor"),
    ):
        if path.exists():
            assert path.is_file(), path
            assert os.access(path, os.X_OK), path

    assert not Path("downloads/versions.json").exists()


def test_phase31a_release_zip_contains_only_runtime_payload() -> None:
    release_zip = Path("downloads/tts-preprocessor.zip")
    if not release_zip.exists():
        return

    with zipfile.ZipFile(release_zip) as archive:
        names = archive.namelist()

    assert "tts-preprocessor/bin/tts_preprocessor" in names
    forbidden = [
        name
        for name in names
        if name.endswith(".py")
        or "/engine/" in name
        or "/docs/" in name
        or "/tests/" in name
    ]
    assert forbidden == []


def test_phase31a_api_server_routes_through_binary_runtime_without_direct_engine_import() -> None:
    tree = ast.parse(Path("api/server.py").read_text(encoding="utf-8"))
    imports: list[str] = []
    post_routes: list[str] = []
    mounts: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "post"
                and isinstance(func.value, ast.Name)
                and func.value.id == "app"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                post_routes.append(str(node.args[0].value))
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "mount"
                and isinstance(func.value, ast.Name)
                and func.value.id == "app"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                mounts.append(str(node.args[0].value))

    assert "api.binary_runtime" in imports
    assert all(not name.startswith("engine") for name in imports)
    assert "/api/transform" in post_routes
    assert "/web" in mounts
    assert "/downloads" in mounts


def test_phase31a_scripts_preserve_remote_runtime_source_absence_contract() -> None:
    start_script = Path("scripts/start_server.sh").read_text(encoding="utf-8")
    deploy_script = Path("scripts/deploy_server.sh").read_text(encoding="utf-8")
    remote_build_script = Path("scripts/build_remote_package.sh").read_text(encoding="utf-8")
    binary_runtime = Path("api/binary_runtime.py").read_text(encoding="utf-8")

    assert "TTS_PREPROCESSOR_BINARY=\"$LATEST_BINARY\"" in start_script
    assert "packages/tts-preprocessor/bin/tts_preprocessor" in start_script
    assert "REMOTE_HOST=\"10.20.10.162\"" in deploy_script
    assert "$REMOTE_BUILD_SRC_DIR/engine/" in deploy_script
    assert "$REMOTE_APP_DIR/engine" in deploy_script
    assert "build_remote_package.sh" in deploy_script
    assert "$VERSION" not in deploy_script
    assert "rm -rf \"$BUILD_SRC_DIR\"" in remote_build_script
    assert "subprocess.run" in binary_runtime
    assert "TTS_PREPROCESSOR_BINARY" in binary_runtime


def test_phase31a_build_package_is_packaging_only() -> None:
    build_package_script = Path("scripts/build_package.py").read_text(encoding="utf-8")
    release_script = Path("scripts/release.py").read_text(encoding="utf-8")

    assert "BUILD_BINARY_SCRIPT" not in build_package_script
    assert "subprocess.run" not in build_package_script
    assert "def build_binary" not in build_package_script
    assert "--binary" in build_package_script
    assert "dist/tts_preprocessor" in build_package_script

    assert "build_binary.sh" in release_script
    assert "\"scripts/build_package.py\"" in release_script
    assert "\"--binary\"" in release_script
    assert "\"dist/tts_preprocessor\"" in release_script
