from __future__ import annotations

import os
import shutil
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


def test_macos_script_rejects_non_python313_project_environment(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    script = project_root / "scripts/build_macos_package.sh"
    script.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script)
    for relative in (
        "tts_preprocessor.spec",
        "bin/build_binary_entrypoint.py",
        "docs/Release_Package_README.txt",
    ):
        target = project_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture\n", encoding="utf-8")

    venv_bin = project_root / ".venv/bin"
    venv_bin.mkdir(parents=True)
    fake_python = venv_bin / "python"
    fake_python.write_text(
        "#!/bin/bash\n"
        "case \"${2:-}\" in\n"
        "  *platform.machine*) printf 'arm64\\n' ;;\n"
        "  *sys.executable*) printf '/fixture/python\\n' ;;\n"
        "  *Py_GIL_DISABLED*) printf '3.10:0\\n' ;;\n"
        "  *) exit 1 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    fake_pyinstaller = venv_bin / "pyinstaller"
    fake_pyinstaller.write_text(
        "#!/bin/bash\nprintf '6.21.0\\n'\n",
        encoding="utf-8",
    )
    fake_pyinstaller.chmod(0o755)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uname = fake_bin / "uname"
    fake_uname.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-s" ]; then printf "Darwin\\n"; '
        'else printf "arm64\\n"; fi\n',
        encoding="utf-8",
    )
    fake_uname.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    result = subprocess.run(
        ["/bin/bash", str(script)],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "standard-GIL Python 3.13.x" in result.stderr


def test_macos_script_uses_project_tools_and_flat_archive_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'PYTHON_BIN="$VENV_DIR/bin/python"' in script
    assert 'PYINSTALLER_BIN="$VENV_DIR/bin/pyinstaller"' in script
    assert 'REQUIRED_PYTHON_SERIES="3.13"' in script
    assert "Py_GIL_DISABLED" in script
    assert '"$PYINSTALLER_BIN"' in script
    assert "\npyinstaller " not in script
    assert "\npython " not in script
    assert "\npython3 " not in script
    assert 'MACOS_BUILD_DIR="$ROOT_DIR/build/macos"' in script
    assert 'PYINSTALLER_CONFIG_DIR="$MACOS_BUILD_DIR/pyinstaller-config"' in script
    assert 'ARCHIVE_NAME="tts-preprocessor-macos.zip"' in script
    assert "tts_preprocessor.spec" in script
    assert "bin/build_binary_entrypoint.py" in script
    assert "pyinstaller_runtime_hooks" not in script
    assert "EXPECTED_CONTENTS=$'README.txt\\ntts-preprocessor'" in script
    assert 'find "$EXTRACT_DIR" -type l' in script
    assert 'mv -f -- "$TEMP_ARCHIVE" "$ARCHIVE_PATH"' in script
