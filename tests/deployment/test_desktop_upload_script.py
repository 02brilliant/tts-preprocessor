from __future__ import annotations

import os
import shutil
import stat
import subprocess
import textwrap
import zipfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = ROOT_DIR / "scripts/upload_desktop_packages.sh"


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, contents in members.items():
            archive.writestr(name, contents)


def _prepare_script_tree(tmp_path: Path) -> tuple[Path, Path]:
    scripts_dir = tmp_path / "scripts"
    downloads_dir = tmp_path / "downloads"
    scripts_dir.mkdir(parents=True)
    downloads_dir.mkdir()
    script = scripts_dir / SOURCE_SCRIPT.name
    shutil.copy2(SOURCE_SCRIPT, script)
    return script, downloads_dir


def _run(
    script: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["/bin/bash", str(script), *args],
        cwd=script.parent.parent,
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(textwrap.dedent(contents).lstrip(), encoding="utf-8")
    path.chmod(0o755)


def _valid_windows_zip(downloads_dir: Path) -> Path:
    archive = downloads_dir / "tts-preprocessor-windows.zip"
    _write_zip(
        archive,
        {
            "tts-preprocessor.exe": b"windows-binary",
            "tts-preprocessor-simplified.exe": b"windows-simplified-binary",
            "tts-preprocessor-llm-minimal.exe": b"windows-llm-minimal-binary",
            "tts-preprocessor-llm-natural.exe": b"windows-llm-natural-binary",
            "tts-preprocessor-llm-pronunciation.exe": b"windows-llm-pronunciation-binary",
            "README.txt": b"readme",
        },
    )
    return archive


def test_windows_upload_requires_exact_platform_and_existing_zip(
    tmp_path: Path,
) -> None:
    script, downloads = _prepare_script_tree(tmp_path)

    missing_platform = _run(script, "--validate-only")
    wrong_platform = _run(
        script, "--platform", "macos", "--validate-only"
    )
    missing_zip = _run(
        script, "--platform", "windows", "--validate-only"
    )

    assert missing_platform.returncode == 2
    assert wrong_platform.returncode == 2
    assert missing_zip.returncode != 0
    assert "Missing Windows ZIP" in missing_zip.stderr
    assert not list(downloads.iterdir())


def test_windows_validate_only_accepts_exact_flat_zip(tmp_path: Path) -> None:
    script, downloads = _prepare_script_tree(tmp_path)
    _valid_windows_zip(downloads)

    result = _run(
        script, "--validate-only", "--platform", "windows"
    )

    assert result.returncode == 0, result.stderr
    assert "Validation-only mode completed" in result.stdout


def test_windows_validation_rejects_extra_source_and_symlink(
    tmp_path: Path,
) -> None:
    source_case = tmp_path / "source-case"
    source_script, source_downloads = _prepare_script_tree(source_case)
    _write_zip(
        source_downloads / "tts-preprocessor-windows.zip",
        {
            "tts-preprocessor.exe": b"binary",
            "tts-preprocessor-simplified.exe": b"binary",
            "tts-preprocessor-llm-minimal.exe": b"binary",
            "tts-preprocessor-llm-natural.exe": b"binary",
            "tts-preprocessor-llm-pronunciation.exe": b"binary",
            "README.txt": b"readme",
            "engine/main.py": b"source",
        },
    )
    source_result = _run(
        source_script, "--platform", "windows", "--validate-only"
    )

    symlink_case = tmp_path / "symlink-case"
    symlink_script, symlink_downloads = _prepare_script_tree(symlink_case)
    with zipfile.ZipFile(
        symlink_downloads / "tts-preprocessor-windows.zip", "w"
    ) as archive:
        link = zipfile.ZipInfo("tts-preprocessor.exe")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "README.txt")
        archive.writestr("tts-preprocessor-simplified.exe", "simplified")
        archive.writestr("tts-preprocessor-llm-minimal.exe", "level3")
        archive.writestr("tts-preprocessor-llm-natural.exe", "level4")
        archive.writestr("tts-preprocessor-llm-pronunciation.exe", "level5")
        archive.writestr("README.txt", "readme")
    symlink_result = _run(
        symlink_script, "--platform", "windows", "--validate-only"
    )

    assert source_result.returncode != 0
    assert "Unexpected Windows ZIP contents" in source_result.stderr
    assert symlink_result.returncode != 0
    assert "symlink" in symlink_result.stderr.lower()


def test_windows_upload_uses_temp_remote_publish_and_simple_http_200(
    tmp_path: Path,
) -> None:
    script, downloads = _prepare_script_tree(tmp_path)
    _valid_windows_zip(downloads)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"

    _write_executable(
        fake_bin / "scp",
        f"""
        #!/usr/bin/env bash
        printf 'scp %s\\n' "$*" >> "{calls}"
        exit 0
        """,
    )
    _write_executable(
        fake_bin / "ssh",
        f"""
        #!/usr/bin/env bash
        printf 'ssh %s\\n' "$*" >> "{calls}"
        cat >/dev/null
        exit 0
        """,
    )
    _write_executable(
        fake_bin / "curl",
        f"""
        #!/usr/bin/env bash
        printf 'curl %s\\n' "$*" >> "{calls}"
        printf '200'
        """,
    )
    env = {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

    result = _run(script, "--platform", "windows", env=env)

    assert result.returncode == 0, result.stderr
    call_text = calls.read_text(encoding="utf-8")
    assert ".tts-preprocessor-windows.zip.upload." in call_text
    assert "tts-preprocessor-windows.zip" in call_text
    assert "tts-preprocessor-linux.zip" not in call_text
    script_text = script.read_text(encoding="utf-8")
    assert 'mv -f -- "$temp_path" "$final_path"' in script_text
    assert "upload-lock" not in script_text
    assert "remote_finalize" not in script_text
    assert "--range" not in script_text
    assert "--platform all" not in script_text


def test_windows_upload_rejects_non_200_http_status(tmp_path: Path) -> None:
    script, downloads = _prepare_script_tree(tmp_path)
    _valid_windows_zip(downloads)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(fake_bin / "scp", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(
        fake_bin / "ssh",
        "#!/usr/bin/env bash\ncat >/dev/null\nexit 0\n",
    )
    _write_executable(
        fake_bin / "curl",
        "#!/usr/bin/env bash\nprintf '503'\n",
    )

    result = _run(
        script,
        "--platform",
        "windows",
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert result.returncode != 0
    assert "HTTP 503" in result.stderr
