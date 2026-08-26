from __future__ import annotations

import os
import zipfile
from pathlib import Path

from scripts import build_package


def test_linux_package_name_and_payload_preserve_desktop_archives(
    tmp_path: Path,
    monkeypatch,
) -> None:
    packages_dir = tmp_path / "packages"
    downloads_dir = tmp_path / "downloads"
    readme = tmp_path / "Release_Package_README.txt"
    binary = tmp_path / "tts_preprocessor"
    simplified_binary = tmp_path / "tts-preprocessor-simplified"
    llm_minimal_binary = tmp_path / "tts-preprocessor-llm-minimal"
    llm_natural_binary = tmp_path / "tts-preprocessor-llm-natural"
    llm_pronunciation_binary = tmp_path / "tts-preprocessor-llm-pronunciation"
    packages_dir.mkdir()
    downloads_dir.mkdir()
    readme.write_text("release readme\n", encoding="utf-8")
    binary.write_bytes(b"prepared-binary")
    binary.chmod(0o755)
    simplified_binary.write_bytes(b"prepared-simplified-binary")
    simplified_binary.chmod(0o755)
    llm_minimal_binary.write_bytes(b"prepared-llm-minimal-binary")
    llm_minimal_binary.chmod(0o755)
    llm_natural_binary.write_bytes(b"prepared-llm-natural-binary")
    llm_natural_binary.chmod(0o755)
    llm_pronunciation_binary.write_bytes(b"prepared-llm-pronunciation-binary")
    llm_pronunciation_binary.chmod(0o755)

    macos_archive = downloads_dir / "tts-preprocessor-macos.zip"
    windows_archive = downloads_dir / "tts-preprocessor-windows.zip"
    unrelated_download = downloads_dir / "keep-me.txt"
    macos_archive.write_bytes(b"macos-sentinel")
    windows_archive.write_bytes(b"windows-sentinel")
    unrelated_download.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(build_package, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(build_package, "PACKAGES_DIR", packages_dir)
    monkeypatch.setattr(build_package, "DOWNLOADS_DIR", downloads_dir)
    monkeypatch.setattr(build_package, "README_TEMPLATE_PATH", readme)

    archive_path = build_package.build_package(binary, simplified_binary, llm_minimal_binary, llm_natural_binary, llm_pronunciation_binary)

    assert archive_path == downloads_dir / "tts-preprocessor-linux.zip"
    assert macos_archive.read_bytes() == b"macos-sentinel"
    assert windows_archive.read_bytes() == b"windows-sentinel"
    assert unrelated_download.read_text(encoding="utf-8") == "keep"

    with zipfile.ZipFile(archive_path) as archive:
        assert sorted(archive.namelist()) == [
            "tts-preprocessor/README.txt",
            "tts-preprocessor/tts-preprocessor",
            "tts-preprocessor/tts-preprocessor-llm-minimal",
            "tts-preprocessor/tts-preprocessor-llm-natural",
            "tts-preprocessor/tts-preprocessor-llm-pronunciation",
            "tts-preprocessor/tts-preprocessor-simplified",
        ]
        assert archive.testzip() is None


def test_linux_package_contains_no_source_payload(tmp_path: Path, monkeypatch) -> None:
    packages_dir = tmp_path / "packages"
    downloads_dir = tmp_path / "downloads"
    readme = tmp_path / "Release_Package_README.txt"
    binary = tmp_path / "tts_preprocessor"
    simplified_binary = tmp_path / "tts-preprocessor-simplified"
    llm_minimal_binary = tmp_path / "tts-preprocessor-llm-minimal"
    llm_natural_binary = tmp_path / "tts-preprocessor-llm-natural"
    llm_pronunciation_binary = tmp_path / "tts-preprocessor-llm-pronunciation"
    readme.write_text("release readme\n", encoding="utf-8")
    binary.write_bytes(b"prepared-binary")
    binary.chmod(0o755)
    simplified_binary.write_bytes(b"prepared-simplified-binary")
    simplified_binary.chmod(0o755)
    llm_minimal_binary.write_bytes(b"prepared-llm-minimal-binary")
    llm_minimal_binary.chmod(0o755)
    llm_natural_binary.write_bytes(b"prepared-llm-natural-binary")
    llm_natural_binary.chmod(0o755)
    llm_pronunciation_binary.write_bytes(b"prepared-llm-pronunciation-binary")
    llm_pronunciation_binary.chmod(0o755)

    monkeypatch.setattr(build_package, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(build_package, "PACKAGES_DIR", packages_dir)
    monkeypatch.setattr(build_package, "DOWNLOADS_DIR", downloads_dir)
    monkeypatch.setattr(build_package, "README_TEMPLATE_PATH", readme)

    archive_path = build_package.build_package(binary, simplified_binary, llm_minimal_binary, llm_natural_binary, llm_pronunciation_binary)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()

    assert os.access(packages_dir / "tts-preprocessor/tts-preprocessor", os.X_OK)
    assert os.access(packages_dir / "tts-preprocessor/tts-preprocessor-simplified", os.X_OK)
    assert os.access(packages_dir / "tts-preprocessor/tts-preprocessor-llm-minimal", os.X_OK)
    assert os.access(packages_dir / "tts-preprocessor/tts-preprocessor-llm-natural", os.X_OK)
    assert os.access(packages_dir / "tts-preprocessor/tts-preprocessor-llm-pronunciation", os.X_OK)
    assert not any(
        name.endswith((".py", ".pyc"))
        or any(part in {"engine", "docs", "tests", ".venv"} for part in Path(name).parts)
        for name in names
    )
