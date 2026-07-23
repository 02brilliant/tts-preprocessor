from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT = ROOT_DIR / "scripts/build_macos_package.sh"


def _run_with_fake_uname(tmp_path: Path, *, os_name: str, architecture: str):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uname = fake_bin / "uname"
    fake_uname.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "-s" ]; then printf "%s\\n" "{os_name}"; '
        f'else printf "%s\\n" "{architecture}"; fi\n',
        encoding="utf-8",
    )
    fake_uname.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return subprocess.run(
        ["/bin/bash", str(SCRIPT)],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_macos_script_rejects_non_darwin(tmp_path: Path) -> None:
    result = _run_with_fake_uname(tmp_path, os_name="Linux", architecture="arm64")

    assert result.returncode != 0
    assert "require Darwin" in result.stderr


def test_macos_script_rejects_non_arm64(tmp_path: Path) -> None:
    result = _run_with_fake_uname(tmp_path, os_name="Darwin", architecture="x86_64")

    assert result.returncode != 0
    assert "Apple Silicon arm64 only" in result.stderr


def test_macos_script_uses_project_tools_and_flat_archive_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'PYTHON_BIN="$VENV_DIR/bin/python"' in script
    assert 'PYINSTALLER_BIN="$VENV_DIR/bin/pyinstaller"' in script
    assert '"$PYINSTALLER_BIN"' in script
    assert "\npyinstaller " not in script
    assert "\npython " not in script
    assert "\npython3 " not in script
    assert 'MACOS_BUILD_DIR="$ROOT_DIR/build/macos"' in script
    assert 'PYINSTALLER_CONFIG_DIR="$MACOS_BUILD_DIR/pyinstaller-config"' in script
    assert 'ARCHIVE_NAME="tts-preprocessor-macos.zip"' in script
    assert "tts_preprocessor.spec" in script
    assert "bin/build_binary_entrypoint.py" in script
    assert "pyinstaller_runtime_hooks/enum_strenum_compat.py" in script
    assert "EXPECTED_CONTENTS=$'README.txt\\ntts-preprocessor'" in script
    assert 'find "$EXTRACT_DIR" -type l' in script
    assert 'mv -f -- "$TEMP_ARCHIVE" "$ARCHIVE_PATH"' in script
