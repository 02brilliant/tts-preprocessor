from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT_DIR = Path(__file__).resolve().parent.parent
PACKAGES_DIR = ROOT_DIR / "packages"
DOWNLOADS_DIR = ROOT_DIR / "downloads"
PACKAGE_NAME = "tts-preprocessor"
ARCHIVE_NAME = "tts-preprocessor.zip"
BUILD_BINARY_SCRIPT = ROOT_DIR / "scripts" / "build_binary.sh"
BINARY_PATH = ROOT_DIR / "dist" / "tts_preprocessor"
README_TEMPLATE_PATH = ROOT_DIR / "docs" / "Release_Package_README.txt"


def build_readme() -> str:
    if not README_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing README template: {README_TEMPLATE_PATH}")

    return README_TEMPLATE_PATH.read_text(encoding="utf-8")


def build_package() -> Path:
    package_dir = PACKAGES_DIR / PACKAGE_NAME
    archive_path = DOWNLOADS_DIR / ARCHIVE_NAME

    build_binary()
    remove_previous_artifacts(package_dir, archive_path)
    create_package_structure(package_dir)
    validate_package_structure(package_dir)
    create_archive(package_dir, archive_path)

    return archive_path


def build_binary() -> None:
    if not BUILD_BINARY_SCRIPT.exists():
        raise FileNotFoundError(f"Missing build script: {BUILD_BINARY_SCRIPT}")

    result = subprocess.run(
        ["bash", str(BUILD_BINARY_SCRIPT)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")

    if result.returncode != 0:
        raise RuntimeError("Binary build failed.")
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Binary not found: {BINARY_PATH}")


def remove_previous_artifacts(current_package_dir: Path, current_archive_path: Path) -> None:
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    for path in PACKAGES_DIR.iterdir():
        if path == current_package_dir:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    for path in DOWNLOADS_DIR.iterdir():
        if path == current_archive_path:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def create_package_structure(package_dir: Path) -> None:
    if package_dir.exists():
        shutil.rmtree(package_dir)

    bin_dir = package_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    (package_dir / "README.txt").write_text(build_readme(), encoding="utf-8")
    binary_target = bin_dir / "tts_preprocessor"
    shutil.copy2(BINARY_PATH, binary_target)
    binary_target.chmod(0o755)


def validate_package_structure(package_dir: Path) -> None:
    forbidden_paths: list[str] = []

    for path in sorted(package_dir.rglob("*")):
        relative = path.relative_to(package_dir)
        relative_text = str(relative)

        if path.is_dir() and relative.parts and relative.parts[0] in {"engine", "docs", "tests"}:
            forbidden_paths.append(relative_text)
            continue

        if path.is_file() and path.suffix == ".py":
            forbidden_paths.append(relative_text)

    if forbidden_paths:
        joined = ", ".join(forbidden_paths)
        raise RuntimeError(f"Package contains forbidden source artifacts: {joined}")


def create_archive(package_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for path in sorted(package_dir.rglob("*")):
            if path.is_dir():
                continue
            zip_file.write(path, path.relative_to(package_dir.parent))


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("Usage: python scripts/build_package.py [ignored-version]", file=sys.stderr)
        return 1

    try:
        archive_path = build_package()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created package: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
